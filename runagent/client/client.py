from runagent.sdk import RunAgentSDK
from runagent.sdk.rest_client import RestClient
from runagent.sdk.socket_client import SocketClient
from runagent.utils.serializer import CoreSerializer
from rich.console import Console
console = Console()


class RunAgentClient:

    def __init__(self, agent_id: str, entrypoint_tag: str, local: bool = True, host: str = None, port: int = None):
        self.sdk = RunAgentSDK()
        self.serializer = CoreSerializer()
        self.local = local
        self.agent_id = agent_id
        self.entrypoint_tag = entrypoint_tag
        
        # FIXED: Detect if this is a streaming entrypoint
        self.is_streaming = entrypoint_tag.endswith("_stream")

        if local:
            if host and port:
                agent_host = host
                agent_port = port
                console.print(f"🔌 [cyan]Using explicit address: {agent_host}:{agent_port}[/cyan]")
            else:
                agent_info = self.sdk.db_service.get_agent(agent_id)
                if not agent_info:
                    raise ValueError(f"Agent {agent_id} not found in local DB")

                self.agent_info = agent_info
                agent_host = self.agent_info["host"]
                agent_port = self.agent_info["port"]

                console.print(f"🔍 [cyan]Auto-resolved address for agent {agent_id}: {agent_host}:{agent_port}[/cyan]")

            agent_base_url_local = f"http://{agent_host}:{agent_port}"
            agent_socket_url_local = f"ws://{agent_host}:{agent_port}"

            self.rest_client = RestClient(base_url=agent_base_url_local)
            self.socket_client = SocketClient(base_socket_url=agent_socket_url_local)
        else:
            self.rest_client = RestClient(is_local=False)
            self.socket_client = SocketClient(is_local=False)

    def run(self, *input_args, **input_kwargs):
        """
        FIXED: Smart execution - automatically uses streaming or non-streaming based on entrypoint
        """
        # FIXED: If this is a streaming entrypoint, automatically use run_stream
        if self.is_streaming:
            console.print(f"[cyan]Detected streaming entrypoint, using WebSocket streaming[/cyan]")
            return self.run_stream(*input_args, **input_kwargs)
        
        # Non-streaming execution (HTTP POST)
        response = self.rest_client.run_agent(
            self.agent_id, self.entrypoint_tag, input_args=input_args, input_kwargs=input_kwargs
        )
        if response.get("success"):
            # Handle new response format with nested data
            if "data" in response and "result_data" in response["data"]:
                response_data = response["data"]["result_data"].get("data")
            else:
                # Fallback to old format for backward compatibility
                response_data = response.get("output_data")
            return self.serializer.deserialize_object(response_data)

        else:
            # Handle new error format with ErrorDetail object
            error_info = response.get("error")
            if isinstance(error_info, dict) and "message" in error_info:
                # New format with ErrorDetail object
                error_message = error_info.get("message", "Unknown error")
                error_code = error_info.get("code", "UNKNOWN_ERROR")
                raise Exception(f"[{error_code}] {error_message}")
            else:
                # Fallback to old format for backward compatibility
                raise Exception(response.get("error", "Unknown error"))

    def run_stream(self, *input_args, **input_kwargs):
        """Stream agent execution results in real-time via WebSocket"""
        try:
            # FIXED: Return the generator directly, don't try to iterate here
            return self.socket_client.run_stream(
                self.agent_id, self.entrypoint_tag, input_args=input_args, input_kwargs=input_kwargs
            )
        except Exception as e:
            # Handle streaming errors with proper formatting
            raise Exception(f"Streaming failed: {str(e)}")

    def _run_stream(self, *input_args, **input_kwargs):
        """Legacy method - use run_stream instead"""
        return self.run_stream(*input_args, **input_kwargs)