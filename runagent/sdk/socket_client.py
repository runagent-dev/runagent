import websockets
import asyncio
from typing import AsyncIterator, Iterator, Optional
from runagent.utils.schema import WebSocketActionType, WebSocketAgentRequest, AgentInputArgs, MessageType, SafeMessage
import json
from typing import Any
from runagent.utils.config import Config
from runagent.utils.serializer import CoreSerializer


class SocketClient:
    """WebSocket client for agent streaming with both async and sync support"""

    def __init__(
        self,
        base_socket_url: Optional[str] = None,
        api_key: Optional[str] = None,
        api_prefix: Optional[str] = "/api/v1"
    ):
        if not base_socket_url:
            base_url = Config.get_base_url()
            base_url = base_url.lstrip("http://").lstrip("https://")
            base_socket_url = f"ws://{base_url}"

        self.base_socket_url = base_socket_url.rstrip("/") + api_prefix
        self.api_key = api_key or Config.get_api_key()
        self.serializer = CoreSerializer()
        
    async def run_agent_generic_stream_async(self, agent_id: str, *input_args, **input_kwargs) -> AsyncIterator[Any]:
        """Stream agent execution results (async version)"""
        uri = f"{self.base_socket_url}/agents/{agent_id}/execute/generic_stream"
        
        async with websockets.connect(uri) as websocket:
            # Send start stream request
            request = WebSocketAgentRequest(
                action=WebSocketActionType.START_STREAM,
                agent_id=agent_id,
                input_data=AgentInputArgs(
                    input_args=input_args,
                    input_kwargs=input_kwargs
                )
            )
            
            start_msg = SafeMessage(
                id="stream_start",
                type=MessageType.STATUS,
                timestamp="",
                data=request.dict()
            )
            
            # Use serialize_message like the sync version
            serialized_msg = self.serializer.serialize_message(start_msg)
            await websocket.send(serialized_msg)
            
            # Receive and yield chunks
            async for raw_message in websocket:
                # Use deserialize_message like the sync version
                safe_msg = self.serializer.deserialize_message(raw_message)
                
                if safe_msg.error:
                    raise Exception(f"Stream error: {safe_msg.error}")
                
                if safe_msg.type == MessageType.STATUS:
                    status = safe_msg.data.get("status")
                    if status == "stream_completed":
                        break
                    elif status == "stream_started":
                        continue  # Skip status messages
                elif safe_msg.type == MessageType.ERROR:
                    raise Exception(f"Agent error: {safe_msg.data}")
                else:
                    # Yield the actual chunk data
                    yield safe_msg.data.get("content", safe_msg.data)

    def run_agent_generic_stream(self, agent_id: str, input_args, input_kwargs) -> Iterator[Any]:
        """Stream agent execution results (sync version)"""
        from websockets.sync.client import connect
        
        uri = f"{self.base_socket_url}/agents/{agent_id}/execute/generic_stream"
        
        with connect(uri) as websocket:

            # Send start stream request
            request = WebSocketAgentRequest(
                action=WebSocketActionType.START_STREAM,
                agent_id=agent_id,
                input_data=AgentInputArgs(
                    input_args=input_args,
                    input_kwargs=input_kwargs
                )
            )
            
            start_msg = SafeMessage(
                id="stream_start",
                type=MessageType.STATUS,
                timestamp="",
                data=request.dict()
            )

            serialized_msg = self.serializer.serialize_message(start_msg)
            websocket.send(serialized_msg)
            
            # Receive and yield chunks
            for raw_message in websocket:
                safe_msg = self.serializer.deserialize_message(raw_message)
                
                if safe_msg.error:
                    raise Exception(f"Stream error: {safe_msg.error}")
                
                if safe_msg.type == MessageType.STATUS:
                    status = safe_msg.data.get("status")
                    if status == "stream_completed":
                        break
                    elif status == "stream_started":
                        continue  # Skip status messages
                elif safe_msg.type == MessageType.ERROR:
                    raise Exception(f"Agent error: {safe_msg.data}")
                else:
                    # Yield the actual chunk data
                    yield safe_msg.data
