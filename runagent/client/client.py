from runagent.sdk import RunAgentSDK
from runagent.sdk.rest_client import RestClient
from runagent.utils.agent import validate_agent, detect_framework


class RunAgentClient:
    def __init__(self, agent_id: str, local: bool = True):
        self.sdk = RunAgentSDK()
        self.agent_id = agent_id
        self.local = local

        if local:
            agent_info = self.sdk.db_manager.get_agent(agent_id)
            if not agent_info:
                raise ValueError(f"Agent {agent_id} not found in local DB")
            self.agent_info = agent_info

            agent_host = self.agent_info['host']
            agent_port = self.agent_info['port']
            agent_base_url = f"http://{agent_host}:{agent_port}"

            self.rest_client = RestClient(
                base_url=agent_base_url,
                api_prefix="/api/v1"
            )
        else:
            self.rest_client = RestClient()

    def run(self, input_args: list = None, input_kwargs: dict = None):
        return self.rest_client.run_agent_generic(
            self.agent_id,
            input_args=input_args,
            input_kwargs=input_kwargs
        )

    def list_agents(self):
        pass
    
    def get_agent_info(self, agent_id: str):
        pass