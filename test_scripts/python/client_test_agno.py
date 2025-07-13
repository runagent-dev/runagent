# from runagent import RunAgentClient

# ra = RunAgentClient(
#     agent_id="3e85fde9-dc89-4b9c-a674-8d4ba09b4b0b",
#     entrypoint_tag="agno_assistant",
#     local=True
#     )


# agent_result = ra.run(
#     "Analyze the benefits of remote work for software teams"
# )

# print(agent_result)
# ==================================

from runagent import RunAgentClient

ra = RunAgentClient(
    agent_id="3e85fde9-dc89-4b9c-a674-8d4ba09b4b0b",
    entrypoint_tag="agno_stream",
    local=True
    )

for chunk in ra.run(
    "Analyze the benefits of remote work for software teams"
):
    print(chunk['content'], end="")
