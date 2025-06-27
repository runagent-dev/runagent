from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
import asyncio
import json
import time
from rich.console import Console
from runagent.utils.serializer import CoreSerializer
from runagent.utils.schema import WebSocketActionType, WebSocketAgentRequest
from typing import Callable, Dict, Any
from runagent.utils.schema import MessageType, SafeMessage

console = Console()


class AgentWebSocketHandler:
    """WebSocket handler for agent streaming"""
    
    def __init__(self, db_service):
        self.db_service = db_service
        self.serializer = CoreSerializer(max_size_mb=10.0)
        self.active_streams = {}
    
    async def handle_agent_stream(self, websocket: WebSocket, agent_id: str, agent_execution_streamer: Callable):
        """Handle WebSocket connection for agent streaming"""
        await websocket.accept()
        connection_id = f"{agent_id}_{int(time.time())}"
        
        try:
            console.print(f"🔌 WebSocket connected for agent: [cyan]{agent_id}[/cyan]")
            
            # Wait for client request
            raw_message = await websocket.receive_text()
            request_msg = self.serializer.deserialize_message(raw_message)
            if request_msg.error:
                await self._send_error(websocket, f"Invalid request: {request_msg.error}")
                return
            
            # Parse WebSocket request
            try:
                ws_request = WebSocketAgentRequest(**request_msg.data)
            except Exception as e:
                await self._send_error(websocket, f"Invalid request format: {str(e)}")
                return
            
            if ws_request.action == WebSocketActionType.START_STREAM:
                await self._handle_stream_start(websocket, ws_request, connection_id, agent_execution_streamer)
            elif ws_request.action == WebSocketActionType.PING:
                await self._send_pong(websocket)
            else:
                await self._send_error(websocket, f"Unknown action: {ws_request.action}")
                    
        except WebSocketDisconnect:
            console.print(f"🔌 WebSocket disconnected for agent: [cyan]{agent_id}[/cyan]")
            self._cleanup_stream(connection_id)
        except Exception as e:
            console.print(f"💥 WebSocket error for agent {agent_id}: [red]{str(e)}[/red]")
            await self._send_error(websocket, f"Server error: {str(e)}")
            self._cleanup_stream(connection_id)
    
    async def _handle_stream_start(self, websocket: WebSocket, request: WebSocketAgentRequest, connection_id: str, agent_execution_streamer: Callable):
        """Handle stream start request"""
        start_time = time.time()
        try:
            
            # Send stream started status
            await self._send_status(websocket, "stream_started", {
                "agent_id": request.agent_id,
                "input_args": request.input_data.input_args,
                "input_kwargs": list(request.input_data.input_kwargs.keys())
            })
            
            console.print(f"🚀 Starting stream for agent: [cyan]{request.agent_id}[/cyan]")
            console.print(f"🔍 Input args: [cyan]{request.input_data.input_args}[/cyan]")
            console.print(f"🔍 Input kwargs: [cyan]{request.input_data.input_kwargs}[/cyan]")
            
            # Track active stream
            self.active_streams[connection_id] = {
                "agent_id": request.agent_id,
                "start_time": start_time,
                "chunk_count": 0
            }
            
            # Start the streaming iteration
            chunk_count = 0
            async for chunk in self._safe_agent_stream(
                agent_execution_streamer,
                *request.input_data.input_args,
                **request.input_data.input_kwargs
            ):
                # Check if stream is still active
                if connection_id not in self.active_streams:
                    break
                
                chunk_count += 1
                self.active_streams[connection_id]["chunk_count"] = chunk_count
                
                raw_data_msg = SafeMessage(
                    id="raw_chunk",
                    type=MessageType.RAW_DATA,
                    timestamp="",
                    data=chunk
                )
                # Send chunk with appropriate message type
                serialized_chunk = self.serializer.serialize_message(raw_data_msg)
                await websocket.send_text(serialized_chunk)
                
                # Small delay to prevent overwhelming the client
                await asyncio.sleep(0)
            
            # Send completion status
            execution_time = time.time() - start_time
            await self._send_status(websocket, "stream_completed", {
                "agent_id": request.agent_id,
                "total_chunks": chunk_count,
                "execution_time": execution_time
            })
            
            # Record successful run in database
            self.db_service.record_agent_run(
                agent_id=request.agent_id,
                input_data=request.input_data.dict(),
                output_data={"stream_completed": True, "chunk_count": chunk_count},
                success=True,
                execution_time=execution_time,
            )
            
            console.print(
                f"✅ Agent [cyan]{request.agent_id}[/cyan] stream completed successfully in "
                f"{execution_time:.2f}s with {chunk_count} chunks"
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Error streaming agent {request.agent_id}: {str(e)}"
            
            await self._send_error(websocket, error_msg)
            
            # Record failed run in database
            self.db_service.record_agent_run(
                agent_id=request.agent_id,
                input_data=request.input_data.dict(),
                output_data=None,
                success=False,
                error_message=error_msg,
                execution_time=execution_time,
            )
            
            console.print(f"💥 [red]{error_msg}[/red]")
        
        finally:
            self._cleanup_stream(connection_id)
    
    async def _safe_agent_stream(self, agent_execution_streamer, *input_args, **input_kwargs):
        """Safely wrap the agent's generic_stream method"""
        try:
            async for chunk in agent_execution_streamer(*input_args, **input_kwargs):
                yield chunk
        except Exception as e:
            # Yield error as final chunk
            yield {
                "error": str(e),
                "error_type": type(e).__name__,
                "input_args": input_args,
                "input_kwargs": input_kwargs
            }
    
    async def _send_status(self, websocket: WebSocket, status: str, data: Dict[str, Any]):
        """Send status message"""
        status_msg = SafeMessage(
            id=status,
            type=MessageType.STATUS,
            timestamp="",
            data={"status": status, **data}
        )
        status_msg = self.serializer.serialize_message(status_msg)
        await websocket.send_text(status_msg)
    
    async def _send_error(self, websocket: WebSocket, error: str):
        """Send error message"""
        error_msg = self.serializer.serialize_object(
            {"error": error}
        )
        await websocket.send_text(error_msg)
    
    async def _send_pong(self, websocket: WebSocket):
        """Send pong response"""
        pong_msg = self.serializer.serialize_object(
            {"pong": True, "timestamp": time.time()}
        )
        await websocket.send_text(pong_msg)
    
    def _cleanup_stream(self, connection_id: str):
        """Clean up stream resources"""
        if connection_id in self.active_streams:
            del self.active_streams[connection_id]