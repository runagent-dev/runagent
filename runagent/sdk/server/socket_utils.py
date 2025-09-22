from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
import os
import asyncio
import json
import time
from datetime import datetime, timezone
import uuid
from rich.console import Console
from runagent.utils.serializer import CoreSerializer
from runagent.utils.schema import WebSocketActionType, WebSocketAgentRequest
from typing import Callable, Dict, Any
from runagent.utils.schema import MessageType, SafeMessage
from runagent.sdk.deployment.middleware_sync import get_middleware_sync
console = Console()


class AgentWebSocketHandler:
    """WebSocket handler for agent streaming - ENHANCED with invocation tracking"""

    def __init__(self, db_service, middleware_sync=None):
        self.db_service = db_service
        self.serializer = CoreSerializer(max_size_mb=10.0)
        self.middleware_sync = middleware_sync or get_middleware_sync()
        self.active_streams = {}

    async def handle_agent_stream(self, websocket: WebSocket, agent_id: str, agent_execution_streamer):
        """ORIGINAL METHOD - Handle WebSocket connection for agent streaming (backward compatibility)"""
        await websocket.accept()
        connection_id = f"{agent_id}_{int(time.time())}"

        try:
            console.print(f" WebSocket connected for agent: [cyan]{agent_id}[/cyan]")
            
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
            console.print(f"WebSocket disconnected for agent: [cyan]{agent_id}[/cyan]")
            self._cleanup_stream(connection_id)
        except Exception as e:
            console.print(f"💥 WebSocket error for agent {agent_id}: [red]{str(e)}[/red]")
            await self._send_error(websocket, f"Server error: {str(e)}")
            self._cleanup_stream(connection_id)

    async def handle_agent_stream_with_tracking(
        self, 
        websocket: WebSocket, 
        agent_id: str, 
        stream_runner, 
        entrypoint_tag: str,
        db_service
    ):
        """Handle streaming execution - FIXED for middleware sync"""
        await websocket.accept()
        
        invocation_id = None
        middleware_invocation_id = None  # FIXED: Add middleware invocation ID tracking
        
        try:
            # Wait for start message
            data = await websocket.receive_text()
            start_message = self.serializer.deserialize_message(data)
            
            request_data = start_message.data
            input_args = request_data.get("input_data", {}).get("input_args", [])
            input_kwargs = request_data.get("input_data", {}).get("input_kwargs", {})
            
            # Start LOCAL invocation tracking first
            invocation_id = self.db_service.start_invocation(
                agent_id=agent_id,
                input_data={
                    "input_args": input_args,
                    "input_kwargs": input_kwargs
                },
                entrypoint_tag=entrypoint_tag,
                sdk_type="websocket_stream",
                client_info={
                    "connection_type": "websocket",
                    "stream_mode": True
                }
            )
            
            console.print(f"🚀 Started invocation: Invocation ID = {invocation_id}")
            console.print(f"🔍 Entrypoint: {entrypoint_tag}")
            console.print(f"🔍 Input data: *{input_args}, **{input_kwargs}")
            
            # FIXED: Sync invocation start to middleware - PROPERLY
            if (hasattr(self, 'middleware_sync') and 
                self.middleware_sync and 
                self.middleware_sync.is_sync_enabled()):
                
                try:
                    console.print(f"📡 [cyan]Syncing invocation start to middleware...[/cyan]")
                    
                    # Prepare sync payload with CORRECT structure
                    sync_payload = {
                        "agent_id": agent_id,  # Main agent ID
                        "local_execution_id": invocation_id,  # This becomes main execution ID in middleware
                        "input_data": {
                            "input_args": input_args,
                            "input_kwargs": input_kwargs
                        },
                        "entrypoint_tag": entrypoint_tag,
                        "sdk_type": "websocket_stream",
                        "client_info": {
                            "connection_type": "websocket",
                            "stream_mode": True,
                            "server_host": "127.0.0.1",  # Add proper server info
                            "server_port": 8450  # Add proper port info
                        }
                    }
                    
                    middleware_invocation_id = await self.middleware_sync.sync_invocation_start(sync_payload)
                    
                    if middleware_invocation_id:
                        console.print(f"✅ [green]Middleware invocation started: {middleware_invocation_id}[/green]")
                    else:
                        console.print(f"⚠️ [yellow]Middleware invocation start failed[/yellow]")
                        
                except Exception as e:
                    console.print(f"❌ [red]Middleware sync start failed: {e}[/red]")
            
            # Send stream started status to client
            await websocket.send_text(self.serializer.serialize_message(
                SafeMessage(
                    id="stream_status",
                    type=MessageType.STATUS,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    data={
                        "status": "stream_started",
                        "invocation_id": invocation_id,
                        "middleware_invocation_id": middleware_invocation_id
                    }
                )
            ))
            
            start_time = time.time()
            chunk_count = 0
            stream_output_data = []
            
            # Run the streaming function
            try:
                async for chunk in stream_runner(*input_args, **input_kwargs):
                    chunk_count += 1
                    
                    # Store chunk for final output tracking (limit to prevent memory issues)
                    if chunk_count <= 5000:
                        try:
                            serializable_chunk = self._convert_to_serializable(chunk)
                            stream_output_data.append(serializable_chunk)
                        except Exception as e:
                            console.print(f"⚠️ [yellow]Warning: Could not serialize chunk {chunk_count}: {e}[/yellow]")
                            stream_output_data.append({
                                "chunk_number": chunk_count,
                                "serialization_error": str(e),
                                "chunk_type": str(type(chunk)),
                                "chunk_preview": str(chunk)
                            })
                    
                    # Send chunk to client
                    chunk_message = SafeMessage(
                        id=f"chunk_{uuid.uuid4()}",
                        type=MessageType.DATA,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        data={"content": chunk}
                    )
                    
                    serialized_chunk = self.serializer.serialize_message(chunk_message)
                    await websocket.send_text(serialized_chunk)
                
                # Streaming completed successfully
                execution_time = time.time() - start_time
                
                console.print(f"✅ Completed invocation {invocation_id[:8]}... successfully")
                console.print(f"📊 Total chunks: {chunk_count}, Execution time: {execution_time:.2f}s")
                
                # FIXED: Complete LOCAL invocation tracking with success
                try:
                    final_output_data = {
                        "stream_completed": True,
                        "total_chunks": chunk_count,
                        "execution_type": "streaming",
                        "sample_chunks": stream_output_data if stream_output_data else [],
                        "execution_time_seconds": execution_time,
                        "chunk_summary": {
                            "total_chunks": chunk_count,
                            "stored_samples": min(len(stream_output_data), 10),
                            "stream_type": "websocket"
                        }
                    }
                    
                    self.db_service.complete_invocation(
                        invocation_id=invocation_id,
                        output_data=final_output_data,
                        execution_time_ms=execution_time * 1000
                    )
                    console.print(f"✅ [green]Local invocation completed successfully[/green]")
                    
                except Exception as e:
                    console.print(f"❌ [red]Failed to complete local invocation: {e}[/red]")
                
                # FIXED: Sync completion to middleware - PROPERLY
                if middleware_invocation_id and self.middleware_sync:
                    try:
                        console.print(f"📡 [cyan]Syncing completion to middleware...[/cyan]")
                        
                        completion_data = {
                            "output_data": final_output_data,
                            "execution_time_ms": execution_time * 1000,
                            "status": "completed"
                        }
                        
                        sync_success = await self.middleware_sync.sync_invocation_complete(
                            middleware_invocation_id,
                            completion_data
                        )
                        
                        if sync_success:
                            console.print(f"✅ [green]Middleware completion synced successfully[/green]")
                        else:
                            console.print(f"❌ [red]Middleware completion sync failed[/red]")
                            
                    except Exception as e:
                        console.print(f"❌ [red]Middleware sync completion error: {e}[/red]")
                
                # Send completion status to client
                await websocket.send_text(self.serializer.serialize_message(
                    SafeMessage(
                        id="stream_complete",
                        type=MessageType.STATUS,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        data={
                            "status": "stream_completed",
                            "total_chunks": chunk_count,
                            "execution_time": execution_time,
                            "invocation_id": invocation_id,
                            "middleware_synced": middleware_invocation_id is not None
                        }
                    )
                ))
                
            except Exception as stream_error:
                if os.getenv('DISABLE_TRY_CATCH'):
                    raise
                # Streaming failed
                execution_time = time.time() - start_time
                error_detail = f"Streaming error: {str(stream_error)}"
                
                console.print(f"❌ [red]Stream execution failed: {error_detail}[/red]")
                
                # Complete LOCAL invocation with error
                self.db_service.complete_invocation(
                    invocation_id=invocation_id,
                    error_detail=error_detail,
                    execution_time_ms=execution_time * 1000
                )
                
                # FIXED: Sync error to middleware - PROPERLY
                if middleware_invocation_id and self.middleware_sync:
                    try:
                        console.print(f"📡 [cyan]Syncing error to middleware...[/cyan]")
                        
                        error_data = {
                            "error_detail": error_detail,
                            "execution_time_ms": execution_time * 1000,
                            "status": "failed"
                        }
                        
                        await self.middleware_sync.sync_invocation_complete(
                            middleware_invocation_id,
                            error_data
                        )
                        console.print(f"✅ [green]Middleware error synced[/green]")
                        
                    except Exception as sync_error:
                        console.print(f"❌ [red]Middleware sync error failed: {sync_error}[/red]")
                
                # Send error to client
                await websocket.send_text(self.serializer.serialize_message(
                    SafeMessage(
                        id="stream_error",
                        type=MessageType.ERROR,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        data={"error": error_detail},
                        error=error_detail
                    )
                ))
        
        except WebSocketDisconnect:
            console.print(f"WebSocket disconnected for agent {agent_id}")
            if invocation_id:
                # Complete local invocation as disconnected
                self.db_service.complete_invocation(
                    invocation_id=invocation_id,
                    error_detail="WebSocket disconnected",
                    execution_time_ms=0
                )
                
                # FIXED: Sync disconnection to middleware
                if middleware_invocation_id and self.middleware_sync:
                    try:
                        await self.middleware_sync.sync_invocation_complete(
                            middleware_invocation_id,
                            {
                                "error_detail": "WebSocket disconnected",
                                "execution_time_ms": 0,
                                "status": "cancelled"
                            }
                        )
                    except Exception as e:
                        console.print(f"Failed to sync disconnection: {e}")
        
        except Exception as e:
            console.print(f"❌ WebSocket handler error: {e}")
            if invocation_id:
                # Complete local invocation with error
                self.db_service.complete_invocation(
                    invocation_id=invocation_id,
                    error_detail=str(e),
                    execution_time_ms=0
                )
                
                # FIXED: Sync handler error to middleware
                if middleware_invocation_id and self.middleware_sync:
                    try:
                        await self.middleware_sync.sync_invocation_complete(
                            middleware_invocation_id,
                            {
                                "error_detail": str(e),
                                "execution_time_ms": 0,
                                "status": "failed"
                            }
                        )
                    except Exception as sync_error:
                        console.print(f"Failed to sync handler error: {sync_error}")

    
    async def _handle_stream_start(self, websocket: WebSocket, request: WebSocketAgentRequest, connection_id: str, agent_execution_streamer: Callable):
        """ORIGINAL METHOD - Handle stream start request (backward compatibility)"""
        start_time = time.time()
        try:
            
            # Send stream started status
            await self._send_status(websocket, "stream_started", {
                "agent_id": request.agent_id,
                "input_args": request.input_data.input_args,
                "input_kwargs": list(request.input_data.input_kwargs.keys())
            })
            
            console.print(f"Starting stream for agent: [cyan]{request.agent_id}[/cyan]")
            console.print(f"Input args: [cyan]{request.input_data.input_args}[/cyan]")
            console.print(f"Input kwargs: [cyan]{request.input_data.input_kwargs}[/cyan]")
            
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
            
            # Record successful run in database (backward compatibility)
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
            
            # Record failed run in database (backward compatibility)
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

    async def _handle_stream_start_with_tracking(
        self, 
        websocket: WebSocket, 
        request: WebSocketAgentRequest, 
        connection_id: str, 
        agent_execution_streamer: Callable,
        invocation_id: str,
        db_service,
        middleware_invocation_id: str = None  
    ):
        """Enhanced stream start with invocation tracking and middleware sync"""
        start_time = time.time()
        chunk_count = 0
        stream_output_data = []
        error_detail = None

        try:
            # Send stream started status
            await self._send_status(websocket, "stream_started", {
                "agent_id": request.agent_id,
                "invocation_id": invocation_id,
                "middleware_invocation_id": middleware_invocation_id,  # NEW: Include middleware ID
                "input_args": request.input_data.input_args,
                "input_kwargs": list(request.input_data.input_kwargs.keys())
            })
            
            console.print(f"Starting tracked stream for agent: [cyan]{request.agent_id}[/cyan] (invocation: {invocation_id}...)")
            if middleware_invocation_id:
                console.print(f"[dim]Middleware invocation: {middleware_invocation_id}...[/dim]")
            
            console.print(f"Input args: [cyan]{request.input_data.input_args}[/cyan]")
            console.print(f"Input kwargs: [cyan]{request.input_data.input_kwargs}[/cyan]")
            
            # Track active stream
            self.active_streams[connection_id] = {
                "agent_id": request.agent_id,
                "invocation_id": invocation_id,
                "middleware_invocation_id": middleware_invocation_id,  # NEW: Track middleware ID
                "start_time": start_time,
                "chunk_count": 0
            }
            
            # Start the streaming iteration
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
                
                # Convert chunk to serializable format before storing
                try:
                    serializable_chunk = self._convert_to_serializable(chunk)
                    
                    # Store chunk for final output tracking (limit to prevent memory issues)
                    if chunk_count <= 100:
                        stream_output_data.append(serializable_chunk)
                    
                except Exception as e:
                    console.print(f"⚠️ [yellow]Warning: Could not serialize chunk {chunk_count}: {e}[/yellow]")
                    # Store a safe representation
                    stream_output_data.append({
                        "chunk_number": chunk_count,
                        "serialization_error": str(e),
                        "chunk_type": str(type(chunk)),
                        "chunk_preview": str(chunk)[:100] + "..." if len(str(chunk)) > 100 else str(chunk)
                    })
                
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
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Send completion status
            await self._send_status(websocket, "stream_completed", {
                "agent_id": request.agent_id,
                "invocation_id": invocation_id,
                "middleware_invocation_id": middleware_invocation_id,  # NEW: Include middleware ID
                "total_chunks": chunk_count,
                "execution_time": execution_time
            })
            
            # Complete local invocation tracking with success
            try:
                db_service.complete_invocation(
                    invocation_id=invocation_id,
                    output_data={
                        "stream_completed": True,
                        "total_chunks": chunk_count,
                        "sample_chunks": stream_output_data[:10] if stream_output_data else [],
                        "execution_time_seconds": execution_time,
                        "chunk_summary": {
                            "total_chunks": chunk_count,
                            "stored_samples": min(len(stream_output_data), 10),
                            "stream_type": "websocket"
                        }
                    },
                    execution_time_ms=execution_time * 1000
                )
                console.print(f"✅ [green]Local invocation tracking completed successfully[/green]")
            except Exception as e:
                console.print(f"❌ [red]Failed to complete local invocation tracking: {str(e)}[/red]")
                # Try to complete with minimal data
                try:
                    db_service.complete_invocation(
                        invocation_id=invocation_id,
                        output_data={
                            "stream_completed": True,
                            "total_chunks": chunk_count,
                            "execution_time_seconds": execution_time,
                            "serialization_note": "Some chunks could not be serialized"
                        },
                        execution_time_ms=execution_time * 1000
                    )
                    console.print(f"✅ [green]Local invocation tracking completed with minimal data[/green]")
                except Exception as e2:
                    console.print(f"❌ [red]Critical: Could not complete local invocation tracking: {str(e2)}[/red]")
            
            # NEW: Sync completion to middleware
            if middleware_invocation_id and self.middleware_sync:
                try:
                    await self.middleware_sync.sync_invocation_complete(
                        middleware_invocation_id,
                        {
                            "output_data": {
                                "stream_completed": True,
                                "total_chunks": chunk_count,
                                "sample_chunks": stream_output_data[:10] if stream_output_data else [],
                                "execution_time_seconds": execution_time,
                                "chunk_summary": {
                                    "total_chunks": chunk_count,
                                    "stored_samples": min(len(stream_output_data), 10),
                                    "stream_type": "websocket"
                                }
                            },
                            "execution_time_ms": execution_time * 1000
                        }
                    )
                    console.print(f"📡 [dim]Stream completion synced to middleware[/dim]")
                except Exception as e:
                    console.print(f"⚠️ [yellow]Failed to sync stream completion to middleware: {e}[/yellow]")
            
            # Record in original agent_runs table for backward compatibility
            self.db_service.record_agent_run(
                agent_id=request.agent_id,
                input_data=request.input_data.dict(),
                output_data={"stream_completed": True, "chunk_count": chunk_count},
                success=True,
                execution_time=execution_time,
            )
            
            console.print(
                f"✅ Agent [cyan]{request.agent_id}[/cyan] tracked stream completed successfully in "
                f"{execution_time:.2f}s with {chunk_count} chunks (invocation: {invocation_id[:8]}...)"
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_detail = f"Error streaming agent {request.agent_id}: {str(e)}"
            
            await self._send_error(websocket, error_detail)
            
            # Complete local invocation tracking with error
            db_service.complete_invocation(
                invocation_id=invocation_id,
                error_detail=error_detail,
                execution_time_ms=execution_time * 1000
            )
            
            # NEW: Sync error to middleware
            if middleware_invocation_id and self.middleware_sync:
                try:
                    await self.middleware_sync.sync_invocation_complete(
                        middleware_invocation_id,
                        {
                            "error_detail": error_detail,
                            "execution_time_ms": execution_time * 1000
                        }
                    )
                except Exception as sync_error:
                    console.print(f"⚠️ [yellow]Failed to sync stream error to middleware: {sync_error}[/yellow]")
            
            # Record failed run in database (backward compatibility)
            self.db_service.record_agent_run(
                agent_id=request.agent_id,
                input_data=request.input_data.dict(),
                output_data=None,
                success=False,
                error_message=error_detail,
                execution_time=execution_time,
            )
            
            console.print(f"💥 [red]{error_detail}[/red] (invocation: {invocation_id[:8]}...)")
        
        finally:
            self._cleanup_stream(connection_id)

    def _convert_to_serializable(self, obj):
        """Convert objects to JSON-serializable format"""
        try:
            # Try direct JSON serialization first
            import json
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            # Handle common non-serializable objects
            if hasattr(obj, '__dict__'):
                # Objects with __dict__ (like TextEvent)
                return {
                    "type": type(obj).__name__,
                    "data": {k: self._convert_to_serializable(v) for k, v in obj.__dict__.items()}
                }
            elif hasattr(obj, '_asdict'):
                # Named tuples
                return {
                    "type": type(obj).__name__,
                    "data": obj._asdict()
                }
            elif hasattr(obj, 'dict'):
                # Pydantic models
                try:
                    return obj.dict()
                except:
                    return {"type": type(obj).__name__, "repr": repr(obj)}
            elif hasattr(obj, 'model_dump'):
                # Pydantic v2 models
                try:
                    return obj.model_dump()
                except:
                    return {"type": type(obj).__name__, "repr": repr(obj)}
            elif isinstance(obj, (list, tuple)):
                # Handle lists/tuples recursively
                return [self._convert_to_serializable(item) for item in obj]
            elif isinstance(obj, dict):
                # Handle dictionaries recursively
                return {k: self._convert_to_serializable(v) for k, v in obj.items()}
            else:
                # Fallback to string representation
                return {
                    "type": type(obj).__name__,
                    "repr": repr(obj)[:500],  # Limit length
                    "str": str(obj)[:500]     # Limit length
                }

    
    async def _safe_agent_stream(self, agent_execution_streamer, *input_args, **input_kwargs):
        """UNCHANGED - Safely wrap the agent's generic_stream method"""
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
        """UNCHANGED - Send status message"""
        status_msg = SafeMessage(
            id=status,
            type=MessageType.STATUS,
            timestamp="",
            data={"status": status, **data}
        )
        status_msg = self.serializer.serialize_message(status_msg)
        await websocket.send_text(status_msg)
    
    async def _send_error(self, websocket: WebSocket, error: str):
        """UNCHANGED - Send error message"""
        error_msg = self.serializer.serialize_object(
            {"error": error}
        )
        await websocket.send_text(error_msg)
    
    async def _send_pong(self, websocket: WebSocket):
        """UNCHANGED - Send pong response"""
        pong_msg = self.serializer.serialize_object(
            {"pong": True, "timestamp": time.time()}
        )
        await websocket.send_text(pong_msg)
    
    def _cleanup_stream(self, connection_id: str):
        """UNCHANGED - Clean up stream resources"""
        if connection_id in self.active_streams:
            del self.active_streams[connection_id]