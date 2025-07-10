from runagent import RunAgentClient

ra = RunAgentClient(
    agent_id="b80aface-9fc3-4db0-b4f8-d1a319215767",
    entrypoint_tag="demo",
    local=True
    )


agent_results = ra.run([
        {"role": "user", "content": "Analyze the benefits of remote work "
         "for software teams"}
])

print(agent_results)

# ==================================

# from runagent import RunAgentClient

# ra = RunAgentClient(
#     agent_id="b80aface-9fc3-4db0-b4f8-d1a319215767",
#     entrypoint_tag="demo2_stream",
#     local=True
#     )

# for chunk in ra.run([
#         {"role": "user", "content": "Analyze the benefits of remote work "
#          "for software teams"}
# ]):
#     print(chunk)
