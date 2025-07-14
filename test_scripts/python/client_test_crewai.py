# from pprint import pprint
# from runagent import RunAgentClient

# ra = RunAgentClient(
#     agent_id="45fdbb9a-61d9-4c21-a2fc-07d9c2c8ac49",
#     entrypoint_tag="research_crew",
#     local=True
#     )

# agent_result = ra.run(
#     topic="AI Agent Deployment"
# )

# pprint(agent_result)
# ==================================

from runagent import RunAgentClient

ra = RunAgentClient(
    agent_id="45fdbb9a-61d9-4c21-a2fc-07d9c2c8ac49",
    entrypoint_tag="extracted_research_crew",
    local=True
    )

agent_result = ra.run(
    topic="AI Agent Deployment"
)

print(agent_result["content"])