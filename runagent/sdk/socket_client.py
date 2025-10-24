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
    """WebSocket client for agent streaming with both async and sync support"""

    def __init__(
        self,
        base_socket_url: Optional[str] = None,
        api_key: Optional[str] = None,
        api_prefix: Optional[str] = "/api/v1",
        is_local: Optional[bool] = True
    ):
        if not base_socket_url:
            base_url = Config.get_base_url()
            base_url = base_url.lstrip("http://").lstrip("https://")
            base_socket_url = f"ws://{base_url}"

        self.is_local = is_local
        self.base_socket_url = base_socket_url.rstrip("/") + api_prefix
        self.api_key = api_key or Config.get_api_key()
        self.serializer = CoreSerializer()
        
    async def run_stream_async(self, agent_id: str, entrypoint_tag: str, *input_args, **input_kwargs) -> AsyncIterator[Any]:
        """Stream agent execution results (async version)"""

        uri = f"{self.base_socket_url}/agents/{agent_id}/run-stream?token={self.api_key}"
        
        async with websockets.connect(
            uri,
            ping_interval=20,
            ping_timeout=60,
            close_timeout=10,
            max_size=10 * 1024 * 1024
        ) as websocket:
            # Send start stream request in the exact format required
            request_data = {
                "entrypoint_tag": entrypoint_tag,
                "input_args": input_args,
                "input_kwargs": input_kwargs,
                "timeout_seconds": 600,  
                "async_execution": False
            }
            # Send the request as direct JSON
            await websocket.send(json.dumps(request_data))
            
            # Receive and yield chunks
            async for raw_message in websocket:
                try:
                    message = json.loads(raw_message)
                except json.JSONDecodeError:
                    continue  # Skip invalid messages
                
                message_type = message.get("type")
                
                if message_type == "error":
                    raise Exception(f"Stream error: {message.get('error')}")
                elif message_type == "status":
                    status = message.get("status")
                    if status == "stream_completed":
                        break
                    elif status == "stream_started":
                        continue  # Skip status messages
                elif message_type == "data":
                    # Yield the actual chunk data
                    yield message.get("content")

    def run_stream(self, agent_id: str, entrypoint_tag: str, input_args, input_kwargs) -> Iterator[Any]:
        """Stream agent execution results (sync version)"""
        from websockets.sync.client import connect
        
        uri = f"{self.base_socket_url}/agents/{agent_id}/run-stream?token={self.api_key}"
        
        # Add proper timeout and keepalive settings
        with connect(
            uri,
            ping_interval=20,      # Send ping every 20 seconds
            ping_timeout=60,       # Wait up to 60 seconds for pong
            close_timeout=10,      # Timeout for closing handshake
            max_size=10 * 1024 * 1024  # 10MB max message size
        ) as websocket:

            # Send start stream request in the exact format required
            request_data = {
                "entrypoint_tag": entrypoint_tag,
                "input_args": input_args,
                "input_kwargs": input_kwargs,
                "timeout_seconds": 600,  
                "async_execution": False
            }
            
            # Send the request as direct JSON
            websocket.send(json.dumps(request_data))
            
            # Receive and yield chunks
            for raw_message in websocket:
                try:
                    message = json.loads(raw_message)
                except json.JSONDecodeError:
                    continue  # Skip invalid messages
                
                message_type = message.get("type")
                
                if message_type == "error":
                    raise Exception(f"Stream error: {message.get('error')}")
                elif message_type == "status":
                    status = message.get("status")
                    if status == "stream_completed":
                        break
                    elif status == "stream_started":
                        continue  # Skip status messages
                elif message_type == "data":
                    # Yield the actual chunk data
                    yield message.get("content")
