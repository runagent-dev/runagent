from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
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
    """WebSocket handler for agent streaming with invocation tracking"""

    def __init__(self, db_service, middleware_sync=None):
        self.db_service = db_service
        self.serializer = CoreSerializer(max_size_mb=10.0)
        self.middleware_sync = middleware_sync or get_middleware_sync()
        self.active_streams = {}

    def _convert_chunk_to_serializable(self, chunk):
        """
        Convert chunk to JSON-serializable format
        Handles various object types including LlamaIndex objects
        """
        # Already serializable types
        if isinstance(chunk, (str, int, float, bool, type(None))):
            return chunk
        
        # Lists and tuples
        if isinstance(chunk, (list, tuple)):
            return [self._convert_chunk_to_serializable(item) for item in chunk]
        
        # Dictionaries
        if isinstance(chunk, dict):
            return {k: self._convert_chunk_to_serializable(v) for k, v in chunk.items()}
        
        # Objects with dict() method (Pydantic v1)
        if hasattr(chunk, 'dict') and callable(chunk.dict):
            try:
                return chunk.dict()
            except:
                pass
        
        # Objects with model_dump() method (Pydantic v2)
        if hasattr(chunk, 'model_dump') and callable(chunk.model_dump):
            try:
                return chunk.model_dump()
            except:
                pass
        
        # Objects with __dict__
        if hasattr(chunk, '__dict__'):
            try:
                return {
                    k: self._convert_chunk_to_serializable(v) 
                    for k, v in chunk.__dict__.items() 
                    if not k.startswith('_')
                }
            except:
                pass
        
        # Try str() as fallback
        try:
            chunk_str = str(chunk)
            # If str() produces something useful, return it
            if chunk_str and chunk_str != f"<{type(chunk).__name__} object at 0x":
                return chunk_str
        except:
            pass
        
        # Last resort: return type name
        return {"type": type(chunk).__name__, "repr": repr(chunk)[:200]}

    async def handle_agent_stream_with_tracking(
        self, 
        websocket: WebSocket, 
        agent_id: str, 
        entrypoint_runner_dict: dict,
        db_service
    ):
        """Handle streaming execution with proper chunk serialization"""
        # Import datetime at function start to avoid scoping issues
        from datetime import datetime as dt
        await websocket.accept()
        
        invocation_id = None
        
        try:
            # Wait for start message
            data = await websocket.receive_text()
            
            try:
                request_data = json.loads(data)
            except json.JSONDecodeError as e:
                await websocket.send_json({
                    "type": "error",
                    "detail": f"Invalid JSON format: {str(e)}"
                })
                await websocket.close(code=1003)
                return
            
            # Validate required fields
            required_fields = ["entrypoint_tag", "input_args", "input_kwargs"]
            for field in required_fields:
                if field not in request_data:
                    await websocket.send_json({
                        "type": "error",
                        "detail": f"Missing required field: {field}"
                    })
                    await websocket.close(code=1003)
                    return
            
            entrypoint_tag = request_data["entrypoint_tag"]

            if entrypoint_tag not in entrypoint_runner_dict:
                await websocket.send_json({
                    "type": "error",
                    "detail": f"Entrypoint {entrypoint_tag} not found"
                })
                await websocket.close(code=1003)
                return

            if not entrypoint_tag.endswith("_stream"):
                await websocket.send_json({
                    "type": "error",
                    "detail": f"Entrypoint `{entrypoint_tag}` is not a streaming entrypoint. Use a streaming entrypoint (ending with '_stream')."
                })
                await websocket.close(code=1003)
                return

            stream_runner = entrypoint_runner_dict[entrypoint_tag]

            input_args = request_data.get("input_args", [])
            input_kwargs = request_data.get("input_kwargs", {})
            
            # Start LOCAL invocation tracking
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
            
            console.print(f"Started invocation: Invocation ID = {invocation_id}")
            
            # Send stream started status
            await websocket.send_json({
                "type": "status",
                "status": "stream_started",
                "invocation_id": invocation_id
            })
            
            start_time = time.time()
            chunk_count = 0
            stream_output_data = []  # Store chunks with timestamps: [(chunk_data, timestamp), ...]
            
            # Run the streaming function
            try:
                async for chunk in stream_runner(*input_args, **input_kwargs):
                    chunk_count += 1
                    chunk_timestamp = dt.now().isoformat() + "Z"
                    
                    # Convert chunk to serializable format
                    try:
                        serializable_chunk = self._convert_chunk_to_serializable(chunk)
                    except Exception as conv_error:
                        console.print(f"Warning: Could not convert chunk {chunk_count}: {conv_error}")
                        serializable_chunk = {
                            "chunk_number": chunk_count,
                            "conversion_error": str(conv_error),
                            "chunk_type": str(type(chunk)),
                            "chunk_str": str(chunk)[:200]
                        }
                    
                    # Store chunk with timestamp for final output tracking (limit to prevent memory issues)
                    if chunk_count <= 5000:
                        try:
                            stream_output_data.append((serializable_chunk, chunk_timestamp))
                        except Exception as e:
                            console.print(f"Warning: Could not store chunk {chunk_count}: {e}")
                    
                    # Send chunk to client using structured serialization
                    try:
                        structured_chunk = self.serializer.serialize_object_to_structured(serializable_chunk)
                        await websocket.send_json({
                            "type": "data",
                            "content": structured_chunk
                        })
                    except Exception as send_error:
                        console.print(f"Error sending chunk {chunk_count}: {send_error}")
                        await websocket.send_json({
                            "type": "error",
                            "error": f"Chunk serialization failed: {str(send_error)}"
                        })
                
                # Streaming completed successfully
                execution_time = time.time() - start_time
                
                console.print(f"Completed invocation {invocation_id[:8]}... successfully")
                console.print(f"Total chunks: {chunk_count}, Execution time: {execution_time:.2f}s")
                
                # Complete LOCAL invocation tracking
                try:
                    # Extract just the chunk data (without timestamps) for local DB storage
                    sample_chunks_data = [chunk_data for chunk_data, _ in stream_output_data[:10]] if stream_output_data else []
                    
                    final_output_data = {
                        "stream_completed": True,
                        "total_chunks": chunk_count,
                        "execution_type": "streaming",
                        "sample_chunks": sample_chunks_data,
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
                    console.print(f"Local invocation completed successfully")
                    
                except Exception as e:
                    console.print(f"Failed to complete local invocation: {e}")
                
                # Sync complete execution to middleware using new unified endpoint
                if (hasattr(self, 'middleware_sync') and 
                    self.middleware_sync and 
                    self.middleware_sync.is_sync_enabled()):
                    
                    try:
                        from runagent.utils.logging_utils import is_verbose_logging_enabled
                        # datetime is already imported at top of file
                        if is_verbose_logging_enabled():
                            console.print(f"Syncing streaming execution to middleware...")
                        
                        # Wrap result_data to match remote streaming execution format
                        # Format: { "stream_chunks": [...], "total_chunks": N, "execution_type": "stream", ... }
                        # stream_output_data contains tuples: (chunk_data, timestamp)
                        stream_chunks = []
                        
                        # Convert chunks to stream_chunks format matching remote execution format
                        # Each item in stream_output_data is a tuple: (chunk_data, timestamp)
                        for idx, chunk_item in enumerate(stream_output_data, 1):
                            if isinstance(chunk_item, tuple) and len(chunk_item) == 2:
                                chunk_data, chunk_timestamp = chunk_item
                            else:
                                # Fallback for old format (if any chunks don't have timestamps)
                                chunk_data = chunk_item
                                chunk_timestamp = dt.now().isoformat() + "Z"
                            
                            stream_chunks.append({
                                "chunk_id": f"chunk_{idx}",
                                "data": chunk_data,
                                "timestamp": chunk_timestamp
                            })
                        
                        # Wrap in standard streaming format matching remote executions
                        result_data_dict = {
                            "stream_chunks": stream_chunks,
                            "total_chunks": chunk_count,
                            "execution_type": "stream",
                            "completed_at": dt.now().isoformat() + "Z",
                            "runtime_seconds": execution_time
                        }
                        
                        execution_data = {
                            "local_execution_id": invocation_id,
                            "entrypoint_tag": entrypoint_tag,
                            "status": "completed",
                            "started_at": dt.fromtimestamp(start_time).isoformat() + "Z",
                            "completed_at": dt.fromtimestamp(time.time()).isoformat() + "Z",
                            "input_data": {
                                "input_args": input_args,
                                "input_kwargs": input_kwargs
                            },
                            "result_data": result_data_dict,
                            "execution_metadata": {
                                "sdk_type": "websocket_stream",
                                "client_info": {
                                    "connection_type": "websocket",
                                    "stream_mode": True,
                                    "server_host": "127.0.0.1",
                                    "server_port": 8450
                                },
                                "runtime_seconds": execution_time
                            }
                        }
                        
                        sync_success = await self.middleware_sync.sync_execution(agent_id, execution_data)
                        
                        if sync_success:
                            console.print(f"✅ Streaming execution synced to middleware successfully")
                        else:
                            console.print(f"⚠️ Middleware sync returned False")
                            
                    except Exception as e:
                        console.print(f"❌ Middleware sync error: {e}")
                        import traceback
                        traceback.print_exc()
                
                # Send completion status (remote-compatible)
                await websocket.send_json({
                    "type": "status",
                    "status": "stream_completed",
                    "total_chunks": chunk_count,
                    "execution_time": execution_time,
                    "invocation_id": invocation_id
                })
                
            except Exception as stream_error:
                # Streaming failed
                execution_time = time.time() - start_time
                error_detail = f"Streaming error: {str(stream_error)}"
                
                # Always print error details, and include traceback if verbose logging is enabled
                console.print(f"Stream execution failed: {error_detail}")
                from runagent.utils.logging_utils import is_verbose_logging_enabled
                if is_verbose_logging_enabled():
                    import traceback
                    console.print(f"[red]Full traceback:[/red]")
                    console.print(f"[dim]{traceback.format_exc()}[/dim]")
                
                # Complete LOCAL invocation with error
                self.db_service.complete_invocation(
                    invocation_id=invocation_id,
                    error_detail=error_detail,
                    execution_time_ms=execution_time * 1000
                )
                
                # Sync failed execution to middleware using new unified endpoint
                if (hasattr(self, 'middleware_sync') and 
                    self.middleware_sync and 
                    self.middleware_sync.is_sync_enabled()):
                    
                    try:
                        from runagent.utils.logging_utils import is_verbose_logging_enabled
                        # datetime is already imported at top of file
                        if is_verbose_logging_enabled():
                            console.print(f"Syncing failed streaming execution to middleware...")
                        
                        # Extract error code from exception if available
                        error_code = "EXECUTION_ERROR"
                        if isinstance(stream_error, Exception):
                            error_type = type(stream_error).__name__
                            if "ValidationError" in error_type:
                                error_code = "VALIDATION_ERROR"
                            elif "ConnectionError" in error_type:
                                error_code = "CONNECTION_ERROR"
                            elif "TimeoutError" in error_type:
                                error_code = "TIMEOUT_ERROR"
                        
                        execution_data = {
                            "local_execution_id": invocation_id,
                            "entrypoint_tag": entrypoint_tag,
                            "status": "failed",
                            "started_at": dt.fromtimestamp(start_time).isoformat() + "Z",
                            "completed_at": dt.fromtimestamp(time.time()).isoformat() + "Z",
                            "input_data": {
                                "input_args": input_args,
                                "input_kwargs": input_kwargs
                            },
                            "error_message": error_detail,
                            "execution_metadata": {
                                "sdk_type": "websocket_stream",
                                "client_info": {
                                    "connection_type": "websocket",
                                    "stream_mode": True,
                                    "server_host": "127.0.0.1",
                                    "server_port": 8450
                                },
                                "runtime_seconds": execution_time,
                                "error_code": error_code
                            }
                        }
                        
                        sync_success = await self.middleware_sync.sync_execution(agent_id, execution_data)
                        
                        if sync_success:
                            console.print(f"✅ Failed streaming execution synced to middleware")
                        else:
                            console.print(f"⚠️ Middleware sync returned False")
                        
                    except Exception as sync_error:
                        console.print(f"❌ Middleware sync error failed: {sync_error}")
                        import traceback
                        traceback.print_exc()
                
                # Send error to client
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": error_detail
                }))
        
        except WebSocketDisconnect:
            console.print(f"WebSocket disconnected for agent {agent_id}")
            if invocation_id:
                self.db_service.complete_invocation(
                    invocation_id=invocation_id,
                    error_detail="WebSocket disconnected",
                    execution_time_ms=0
                )
                
                # Sync cancelled execution to middleware using new unified endpoint
                if (hasattr(self, 'middleware_sync') and 
                    self.middleware_sync and 
                    self.middleware_sync.is_sync_enabled() and
                    invocation_id):
                    
                    try:
                        from runagent.utils.logging_utils import is_verbose_logging_enabled
                        from datetime import datetime
                        
                        execution_data = {
                            "local_execution_id": invocation_id,
                            "entrypoint_tag": entrypoint_tag if 'entrypoint_tag' in locals() else "unknown",
                            "status": "failed",
                            "started_at": dt.fromtimestamp(start_time).isoformat() + "Z" if 'start_time' in locals() else dt.now().isoformat() + "Z",
                            "completed_at": dt.now().isoformat() + "Z",
                            "input_data": {
                                "input_args": input_args if 'input_args' in locals() else [],
                                "input_kwargs": input_kwargs if 'input_kwargs' in locals() else {}
                            },
                            "error_message": "WebSocket disconnected",
                            "execution_metadata": {
                                "sdk_type": "websocket_stream",
                                "client_info": {
                                    "connection_type": "websocket",
                                    "stream_mode": True,
                                    "server_host": "127.0.0.1",
                                    "server_port": 8450
                                },
                                "runtime_seconds": 0,
                                "error_code": "WEBSOCKET_DISCONNECTED"
                            }
                        }
                        
                        await self.middleware_sync.sync_execution(agent_id, execution_data)
                    except Exception as e:
                        console.print(f"❌ Failed to sync disconnection: {e}")
        
        except Exception as e:
            console.print(f"WebSocket handler error: {e}")
            if invocation_id:
                self.db_service.complete_invocation(
                    invocation_id=invocation_id,
                    error_detail=str(e),
                    execution_time_ms=0
                )
                
                # Sync failed execution to middleware using new unified endpoint
                if (hasattr(self, 'middleware_sync') and 
                    self.middleware_sync and 
                    self.middleware_sync.is_sync_enabled() and
                    invocation_id):
                    
                    try:
                        from runagent.utils.logging_utils import is_verbose_logging_enabled
                        from datetime import datetime
                        
                        execution_data = {
                            "local_execution_id": invocation_id,
                            "entrypoint_tag": entrypoint_tag if 'entrypoint_tag' in locals() else "unknown",
                            "status": "failed",
                            "started_at": dt.fromtimestamp(start_time).isoformat() + "Z" if 'start_time' in locals() else dt.now().isoformat() + "Z",
                            "completed_at": dt.now().isoformat() + "Z",
                            "input_data": {
                                "input_args": input_args if 'input_args' in locals() else [],
                                "input_kwargs": input_kwargs if 'input_kwargs' in locals() else {}
                            },
                            "error_message": str(e),
                            "execution_metadata": {
                                "sdk_type": "websocket_stream",
                                "client_info": {
                                    "connection_type": "websocket",
                                    "stream_mode": True,
                                    "server_host": "127.0.0.1",
                                    "server_port": 8450
                                },
                                "runtime_seconds": 0,
                                "error_code": "HANDLER_ERROR"
                            }
                        }
                        
                        await self.middleware_sync.sync_execution(agent_id, execution_data)
                    except Exception as sync_error:
                        console.print(f"Failed to sync handler error: {sync_error}")

    async def handle_agent_stream(self, websocket: WebSocket, agent_id: str, agent_execution_streamer):
        """ORIGINAL METHOD - Handle WebSocket connection for agent streaming (backward compatibility)"""
        await websocket.accept()
        connection_id = f"{agent_id}_{int(time.time())}"

        try:
            console.print(f"WebSocket connected for agent: {agent_id}")
            
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
            console.print(f"WebSocket disconnected for agent: {agent_id}")
            self._cleanup_stream(connection_id)
        except Exception as e:
            console.print(f"WebSocket error for agent {agent_id}: {str(e)}")
            await self._send_error(websocket, f"Server error: {str(e)}")
            self._cleanup_stream(connection_id)

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
            
            console.print(f"Starting stream for agent: {request.agent_id}")
            console.print(f"Input args: {request.input_data.input_args}")
            console.print(f"Input kwargs: {request.input_data.input_kwargs}")
            
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
                f"Agent {request.agent_id} stream completed successfully in "
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
            
            console.print(f"{error_msg}")
        
        finally:
            self._cleanup_stream(connection_id)
    
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