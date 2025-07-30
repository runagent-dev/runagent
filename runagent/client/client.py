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

        self.agent_architecture = self.rest_client.get_agent_architecture(agent_id)

        selected_entrypoint = next(
            (
                entrypoint for entrypoint in self.agent_architecture['entrypoints']
                if entrypoint['tag'] == entrypoint_tag
            ), None)

        if not selected_entrypoint:
            raise ValueError(f"Entrypoint `{entrypoint_tag}` not found in agent {agent_id}")

    def _run(self, *input_args, **input_kwargs):

        response = self.rest_client.run_agent(
            self.agent_id, self.entrypoint_tag, input_args=input_args, input_kwargs=input_kwargs
        )
        if response.get("success"):
            response_data = response.get("output_data")
            return self.serializer.deserialize_object(response_data)

        else:
            raise Exception(response.get("error"))

    def _run_stream(self, *input_args, **input_kwargs):
        return self.socket_client.run_stream(
            self.agent_id, self.entrypoint_tag, input_args=input_args, input_kwargs=input_kwargs
        )

    def run(self, *input_args, **input_kwargs):
        if self.entrypoint_tag.endswith("_stream"):
            return self._run_stream(*input_args, **input_kwargs)
        else:
            return self._run(*input_args, **input_kwargs)
