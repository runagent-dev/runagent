from runagent import RunAgentClient

ra = RunAgentClient(
    agent_id="ae29bd73-b3d3-99c8-a98f-5d7aec7ee911",
    entrypoint_tag="agno_print_response",
    local=True,
    port=8455
    )


agent_result = ra.run(
    "what is the difference between astrology and love"
)

print(agent_result)
# ==================================

# from runagent import RunAgentClient

# ra = RunAgentClient(
#     agent_id="ae29bd73-b3d3-99c8-a98f-5d7aec7ee911",
#     entrypoint_tag="agno_print_response_stream",
#     local=False
#     )

# for chunk in ra.run(
#     "Benefits of a long drive"
# ):
#     print(chunk)
