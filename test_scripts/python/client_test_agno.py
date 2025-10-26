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
    agent_id="af662135-5c00-4a89-b947-300e34787f03",
    entrypoint_tag="agno_print_response_stream",
    local=False
    )

for chunk in ra.run(
    "Benefits of a long drive"
):
    print(chunk)
