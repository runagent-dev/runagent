from runagent.sdk import RunAgentSDK
from runagent.sdk.rest_client import RestClient
from runagent.utils.agent import detect_framework, validate_agent
from runagent.sdk.socket_client import SocketClient
from runagent.utils.serializer import CoreSerializer


class RunAgentClient:
    def __init__(self, agent_id: str, local: bool = True, host: str = None, port: int = None):
        self.sdk = RunAgentSDK()
        self.agent_id = agent_id
        self.local = local
        self.serializer = CoreSerializer()

        if local:
            if host and port:
                agent_host = host
                agent_port = port
            else:
                agent_info = self.sdk.db_service.get_agent(agent_id)
                if not agent_info:
                    raise ValueError(f"Agent {agent_id} not found in local DB")
                self.agent_info = agent_info

                agent_host = self.agent_info["host"]
                agent_port = self.agent_info["port"]

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
        response = self.rest_client.run_agent_generic(
            self.agent_id, input_args=input_args, input_kwargs=input_kwargs
        )
        if response.get("success"):
            response_data = response.get("output_data")
            return self.serializer.deserialize_object(response_data)

        else:
            raise Exception(response.get("error"))

    def run_generic_stream(self, *input_args, **input_kwargs):
        return self.socket_client.run_agent_generic_stream(
            self.agent_id, input_args=input_args, input_kwargs=input_kwargs
        )


class AsyncRunAgentClient(RunAgentClient):

    async def run_generic(self, *input_args, **input_kwargs):
        response = self.rest_client.run_agent_generic(
            self.agent_id, input_args=input_args, input_kwargs=input_kwargs
        )
        if response.get("success"):
            response_data = response.get("output_data")
            return self.serializer.deserialize_object(response_data)

        else:
            raise Exception(response.get("error"))

    async def run_generic_stream(self, *input_args, **input_kwargs):
        async for item in self.socket_client.run_agent_generic_stream_async(
            self.agent_id, *input_args, **input_kwargs
        ):
            yield item
