from runagent.sdk import RunAgentSDK
from runagent.sdk.rest_client import RestClient
from runagent.utils.agent import detect_framework, validate_agent
from runagent.sdk.socket_client import SocketClient
import requests


class RunAgentClient:
    def __init__(self, agent_id: str, local: bool = True, port: int = None, host: str = None):
        self.sdk = RunAgentSDK()
        self.agent_id = agent_id
        self.local = local

        if local:
            agent_info = self.sdk.db_service.get_agent(agent_id)
            if not agent_info:
                raise ValueError(f"Agent {agent_id} not found in local DB")
            self.agent_info = agent_info

            # Use provided port/host or fall back to database values
            agent_host = host or self.agent_info["host"]
            agent_port = port or self.agent_info["port"]
            
            # Try to connect to the specified port first
            if port is not None:
                test_url = f"http://{agent_host}:{port}/api/v1/health"
                try:
                    response = requests.get(test_url, timeout=2)
                    if response.status_code == 200:
                        agent_port = port
                        print(f"✅ Connected to server on port {port}")
                    else:
                        print(f"⚠️ Server on port {port} returned status {response.status_code}, using database port {agent_port}")
                except requests.exceptions.RequestException:
                    print(f"⚠️ Could not connect to port {port}, using database port {agent_port}")
            
            agent_base_url = f"http://{agent_host}:{agent_port}"
            agent_socket_url = f"ws://{agent_host}:{agent_port}"

            self.rest_client = RestClient(base_url=agent_base_url, api_prefix="/api/v1")
            self.socket_client = SocketClient(
                base_socket_url=agent_socket_url,
                api_prefix="/api/v1"
            )
        else:
            self.rest_client = RestClient()
            self.socket_client = SocketClient()

    def run_generic(self, *input_args, **input_kwargs):
        """
        Run agent with generic interface - simplified for easy testing
        
        Args:
            *input_args: Can be a simple string message or complex arguments
            **input_kwargs: Keyword arguments for the agent
            
        Returns:
            Agent response
        """
        # Handle simple string input
        if len(input_args) == 1 and isinstance(input_args[0], str) and not input_kwargs:
            # Convert simple string to messages format
            input_kwargs = {
                "messages": [{"role": "user", "content": input_args[0]}]
            }
            input_args = ()
        
        return self.rest_client.run_agent_generic(
            self.agent_id, input_args=input_args, input_kwargs=input_kwargs
        )

    def run_generic_stream(self, *input_args, **input_kwargs):
        return self.socket_client.run_agent_generic_stream(
            self.agent_id, input_args=input_args, input_kwargs=input_kwargs
        )


class AsyncRunAgentClient(RunAgentClient):

    async def run_generic(self, *input_args, **input_kwargs):
        return self.rest_client.run_agent_generic(
            self.agent_id, input_args=input_args, input_kwargs=input_kwargs
        )

    async def run_generic_stream(self, *input_args, **input_kwargs):
        async for item in self.socket_client.run_agent_generic_stream_async(
            self.agent_id, *input_args, **input_kwargs
        ):
            yield item