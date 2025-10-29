import websockets
import asyncio
from typing import AsyncIterator, Iterator, Optional
from runagent.utils.schema import WebSocketActionType, WebSocketAgentRequest, MessageType, SafeMessage
import json
import uuid
from typing import Any
from runagent.utils.config import Config
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
        
        print(f"[DEBUG] SocketClient initialized:")
        print(f"  - is_local: {self.is_local}")
        print(f"  - base_socket_url: {self.base_socket_url}")
        print(f"  - api_key: {'SET' if self.api_key else 'NOT SET'}")
        
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
            
            print(f"[DEBUG] Sending request: {request_data}")
            
            # Send the request as direct JSON
            await websocket.send(json.dumps(request_data))
            
            # Receive and yield chunks
            async for raw_message in websocket:
                try:
                    message = json.loads(raw_message)
                except json.JSONDecodeError:
                    print(f"[WARN] Invalid JSON message: {raw_message}")
                    continue
                
                message_type = message.get("type")
                
                if message_type == "error":
                    error_msg = message.get('error') or message.get('detail', 'Unknown error')
                    raise Exception(f"Stream error: {error_msg}")
                elif message_type == "status":
                    status = message.get("status")
                    if status == "stream_completed":
                        print("[DEBUG] Stream completed")
                        break
                    elif status == "stream_started":
                        print("[DEBUG] Stream started")
                        continue
                elif message_type == "data":
                    # Yield the actual chunk data
                    yield message.get("content")

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
            
            print(f"[DEBUG] Sending request: {request_data}")
            
            # Send the request as direct JSON
            websocket.send(json.dumps(request_data))
            
            # Receive and yield chunks
            for raw_message in websocket:
                try:
                    message = json.loads(raw_message)
                except json.JSONDecodeError:
                    print(f"[WARN] Invalid JSON message: {raw_message}")
                    continue
                
                message_type = message.get("type")
                
                if message_type == "error":
                    error_msg = message.get('error') or message.get('detail', 'Unknown error')
                    raise Exception(f"Stream error: {error_msg}")
                elif message_type == "status":
                    status = message.get("status")
                    if status == "stream_completed":
                        print("[DEBUG] Stream completed")
                        break
                    elif status == "stream_started":
                        print("[DEBUG] Stream started")
                        continue
                elif message_type == "data":
                    # Yield the actual chunk data
                    yield message.get("content")