from runagent import RunAgentClient

ra = RunAgentClient(
    agent_id="27f68f00-e8cd-4965-9b91-fac501e132e3",
    entrypoint_tag="agno_print_response",
    local=True
    )


agent_result = ra.run(
    "what is the difference between astrology and love"
)

print(agent_result)
# ==================================

# from runagent import RunAgentClient

# ra = RunAgentClient(
#     agent_id=" 27f68f00-e8cd-4965-9b91-fac501e132e3",
#     entrypoint_tag="agno_stream",
#     local=True
#     )

# for chunk in ra.run(
#     "Benefits of a long drive"
# ):
#     print(chunk['content'], end="")
