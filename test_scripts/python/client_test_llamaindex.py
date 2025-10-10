# from runagent import RunAgentClient

# ra = RunAgentClient(
#     agent_id="583d497b-cb6b-4558-b489-cba8f66e57a1",
#     entrypoint_tag="math_run",
#     local=True
#     )


# agent_result = ra.run(
#     "What is 2 * 3?"
# )

# print(agent_result)
# ==================================

from runagent import RunAgentClient

ra = RunAgentClient(
    agent_id="583d497b-cb6b-4558-b489-cba8f66e57a1",
    entrypoint_tag="math_stream",
    local=True
    )


for chunk in ra.run(
    "What is 2 * 3?"
):
    print(chunk)