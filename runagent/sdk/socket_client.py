import asyncio
import json
import os
import re
import uuid
from typing import Any, AsyncIterator, Iterator, Optional

import websockets

from runagent.utils.config import Config
from runagent.utils.schema import MessageType, SafeMessage, WebSocketActionType, WebSocketAgentRequest
from runagent.utils.serializer import CoreSerializer


class SocketClient:
    """WebSocket client for agent streaming with both async and sync support
    
    FIXED: Now properly handles cloud deployments with correct WSS URLs
    """

    def __init__(
        self,
        base_socket_url: Optional[str] = None,
        api_key: Optional[str] = None,
        api_prefix: Optional[str] = "/api/v1",
        is_local: Optional[bool] = True
    ):
        self.is_local = is_local
        self.api_key = api_key or Config.get_api_key()
        self.serializer = CoreSerializer()
        
        # FIXED: Handle cloud vs local URL construction
        if base_socket_url:
            # Use provided URL
            self.base_socket_url = base_socket_url.rstrip("/") + api_prefix
        else:
            if is_local:
                # Local: Use localhost
                base_url = "ws://127.0.0.1:8450"
                self.base_socket_url = base_url + api_prefix
            else:
                # Cloud: Convert HTTP(S) base URL to WS(S)
                base_url = Config.get_base_url()
                
                # Convert https:// to wss:// or http:// to ws://
                if base_url.startswith("https://"):
                    ws_base = base_url.replace("https://", "wss://")
                elif base_url.startswith("http://"):
                    ws_base = base_url.replace("http://", "ws://")
                else:
                    # No protocol, assume secure for cloud
                    ws_base = f"wss://{base_url}"
                
                self.base_socket_url = ws_base.rstrip("/") + api_prefix
        
        self._debug("SocketClient initialized:")
        self._debug(f"  - is_local: {self.is_local}")
        self._debug(f"  - base_socket_url: {self.base_socket_url}")
        self._debug(f"  - api_key: {'SET' if self.api_key else 'NOT SET'}")
        
    async def run_stream_async(self, agent_id: str, entrypoint_tag: str, *input_args, **input_kwargs) -> AsyncIterator[Any]:
        """Stream agent execution results (async version)"""

        # FIXED: Build proper cloud URL with query param auth
        if self.is_local:
            uri = f"{self.base_socket_url}/agents/{agent_id}/run-stream"
        else:
            # Cloud: Add token as query parameter
            uri = f"{self.base_socket_url}/agents/{agent_id}/run-stream?token={self.api_key}"
        
        # print(f"[DEBUG] Connecting to: {uri}")
        
        # FIXED: Add proper headers for cloud authentication
        extra_headers = {}
        if not self.is_local and self.api_key:
            extra_headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            async with websockets.connect(
                uri,
                extra_headers=extra_headers if extra_headers else None,
                ping_interval=20,
                ping_timeout=60,
                close_timeout=10,
                max_size=10 * 1024 * 1024
            ) as websocket:
                # Send start stream request in the exact format required
                request_data = {
                    "entrypoint_tag": entrypoint_tag,
                    "input_args": list(input_args),  # Ensure JSON serializable
                    "input_kwargs": dict(input_kwargs),  # Ensure JSON serializable
                    "timeout_seconds": 600,  
                    "async_execution": False
                }
                
                self._debug(f"Sending request: {request_data}")
                
                # Send the request as direct JSON
                await websocket.send(json.dumps(request_data))
                
                # Receive and yield chunks
                async for raw_message in websocket:
                    try:
                        message = json.loads(raw_message)
                    except json.JSONDecodeError:
                        self._debug(f"[WARN] Invalid JSON message: {raw_message}")
                        continue
                    
                    message_type = message.get("type")
                    
                    if message_type == "error":
                        error_msg = message.get('error') or message.get('detail', 'Unknown error')
                        cleaned_msg = self._clean_error_message(error_msg)
                        raise Exception(cleaned_msg)
                    elif message_type == "status":
                        status = message.get("status")
                        if status == "stream_completed":
                            self._debug("Stream completed")
                            break
                        elif status == "stream_started":
                            self._debug("Stream started")
                            continue
                    elif message_type == "data":
                        content = message.get("content")
                        if content is None:
                            yield None
                        else:
                            # Try structured deserialization first
                            if isinstance(content, str):
                                try:
                                    yield self.serializer.deserialize_object_from_structured(content)
                                    continue
                                except Exception:
                                    pass
                                try:
                                    yield self.serializer.deserialize_object(content)
                                    continue
                                except Exception:
                                    yield content
                                    continue
                            # Non-string content (fallback/legacy)
                            try:
                                yield self.serializer.deserialize_object(content)
                            except Exception:
                                yield content
                    else:
                        self._debug(f"[WARN] Unknown message type: {message_type}")
        except Exception as e:
            # Clean up WebSocket connection errors
            error_msg = str(e)
            cleaned_msg = self._clean_error_message(error_msg)
            raise Exception(cleaned_msg)

    def run_stream(self, agent_id: str, entrypoint_tag: str, input_args, input_kwargs) -> Iterator[Any]:
        """Stream agent execution results (sync version)"""
        from websockets.sync.client import connect
        
        # FIXED: Build proper cloud URL with query param auth
        if self.is_local:
            uri = f"{self.base_socket_url}/agents/{agent_id}/run-stream"
        else:
            # Cloud: Add token as query parameter
            uri = f"{self.base_socket_url}/agents/{agent_id}/run-stream?token={self.api_key}"
        
        # print(f"[DEBUG] Connecting to: {uri}")
        
        # FIXED: Add proper headers for cloud authentication
        extra_headers = {}
        if not self.is_local and self.api_key:
            extra_headers["Authorization"] = f"Bearer {self.api_key}"
        
        # Add proper timeout and keepalive settings
        try:
            with connect(
                uri,
                additional_headers=extra_headers if extra_headers else None,
                ping_interval=20,      # Send ping every 20 seconds
                ping_timeout=60,       # Wait up to 60 seconds for pong
                close_timeout=10,      # Timeout for closing handshake
                max_size=10 * 1024 * 1024,  # 10MB max message size
                open_timeout=30  # FIXED: Add connection timeout
            ) as websocket:

                # Send start stream request in the exact format required
                request_data = {
                    "entrypoint_tag": entrypoint_tag,
                    "input_args": list(input_args) if input_args else [],
                    "input_kwargs": dict(input_kwargs) if input_kwargs else {},
                    "timeout_seconds": 600,  
                    "async_execution": False
                }
                
                self._debug(f"Sending request: {request_data}")
                
                # Send the request as direct JSON
                websocket.send(json.dumps(request_data))
                
                # Receive and yield chunks
                for raw_message in websocket:
                    try:
                        message = json.loads(raw_message)
                    except json.JSONDecodeError:
                        self._debug(f"[WARN] Invalid JSON message: {raw_message}")
                        continue
                    
                    message_type = message.get("type")
                    
                    if message_type == "error":
                        error_msg = message.get('error') or message.get('detail', 'Unknown error')
                        cleaned_msg = self._clean_error_message(error_msg)
                        raise Exception(cleaned_msg)
                    elif message_type == "status":
                        status = message.get("status")
                        if status == "stream_completed":
                            self._debug("Stream completed")
                            break
                        elif status == "stream_started":
                            self._debug("Stream started")
                            continue
                    elif message_type == "data":
                        content = message.get("content")
                        if content is None:
                            yield None
                        else:
                            if isinstance(content, str):
                                try:
                                    yield self.serializer.deserialize_object_from_structured(content)
                                    continue
                                except Exception:
                                    pass
                                try:
                                    yield self.serializer.deserialize_object(content)
                                    continue
                                except Exception:
                                    yield content
                                    continue
                            try:
                                yield self.serializer.deserialize_object(content)
                            except Exception:
                                yield content
                    else:
                        self._debug(f"[WARN] Unknown message type: {message_type}")
        except Exception as e:
            # Clean up WebSocket connection errors
            error_msg = str(e)
            cleaned_msg = self._clean_error_message(error_msg)
            raise Exception(cleaned_msg)

    def _clean_error_message(self, error_message: str) -> str:
        """Clean up error messages by removing redundant prefixes"""
        if not error_message:
            return "Unknown error"
        
        # Remove common redundant prefixes
        prefixes_to_remove = [
            "received 1011 (internal error) ",
            "Internal server error: ",
            "Server error: ",
            "Database error: ",
            "HTTP Error: ",
            "Stream error: ",
            "Streaming failed: ",
        ]
        
        cleaned = error_message
        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        
        # Remove status codes that appear at the start (e.g., "500: ", "403: ")
        cleaned = re.sub(r'^\d{3}:\s*', '', cleaned)
        
        # Remove duplicate error messages (e.g., "error; then sent error")
        if "; then sent" in cleaned.lower():
            # Extract just the first part before "; then sent"
            cleaned = cleaned.split("; then sent")[0].strip()
        
        # Check if this is a permission error and provide a clean message
        if ("403" in cleaned or "permission" in cleaned.lower() or 
            "access denied" in cleaned.lower() or "do not have permission" in cleaned.lower()):
            return "You do not have permission to access this agent"
        
        return cleaned.strip() if cleaned.strip() else error_message

    def _debug(self, message: str) -> None:
        if os.getenv("RUNAGENT_DEBUG") or os.getenv("DISABLE_TRY_CATCH"):
            if isinstance(message, str) and message.startswith("["):
                print(message)
            else:
                print(f"[DEBUG] {message}")