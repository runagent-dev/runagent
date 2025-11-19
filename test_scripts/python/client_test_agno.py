# from runagent import RunAgentClient

# ra = RunAgentClient(
#     agent_id="55ddf000-0000-0000-0000-000000000000",
#     entrypoint_tag="agno_print_response",
#     local=False
#     )


# agent_result = ra.run(
#     "what is the difference between astrology and love"
# )

# print(agent_result)
# ==================================

from runagent import RunAgentClient

ra = RunAgentClient(
    agent_id="ad29bd73-b3d3-42c8-a98f-5d7aec7ee919",
    entrypoint_tag="agno_print_response_stream",
    local=False
    )

for chunk in ra.run(
    "Benefits of a long drive"
):
    print(chunk)
