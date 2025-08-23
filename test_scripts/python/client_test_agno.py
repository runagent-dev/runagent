# from runagent import RunAgentClient

# ra = RunAgentClient(
#     agent_id="c7a08c39-9086-436b-b64e-399779f5a7e8",
#     entrypoint_tag="agno_assistant",
#     local=True
#     )


# agent_result = ra.run(
#     "what is the difference between astrology and love"
# )

# print(agent_result)
# ==================================

from runagent import RunAgentClient

ra = RunAgentClient(
    agent_id="c7a08c39-9086-436b-b64e-399779f5a7e8",
    entrypoint_tag="agno_stream",
    local=True
    )

for chunk in ra.run(
    "Benefits of a long drive"
):
    print(chunk['content'], end="")
