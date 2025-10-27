# from runagent import RunAgentClient

# ra = RunAgentClient(
#     agent_id="71b31b58-c2d6-49ab-b564-d72b1a449df7",
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
    agent_id="c12d3486-cbf6-4d3a-b58b-e5a9c0dfe311",
    entrypoint_tag="agno_print_response_stream",
    local=False
    )

for chunk in ra.run(
    "Benefits of a long drive"
):
    print(chunk)
