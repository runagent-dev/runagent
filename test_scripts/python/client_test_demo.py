from runagent import RunAgentClient

ra = RunAgentClient(
    agent_id="8f266444-72aa-4e6e-9173-0173b8ded54f",
    entrypoint_tag="minimal",
    local=True
    )


agent_results = ra.run(
    role="user",
    message="Analyze the benefits of remote work for software teams"
)

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
