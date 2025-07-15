# from runagent import RunAgentClient

# ra = RunAgentClient(
#     agent_id="408db172-a58b-41f3-b396-0e182784749d",
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
    agent_id="408db172-a58b-41f3-b396-0e182784749d",
    entrypoint_tag="math_stream",
    local=True
    )

for chunk in ra.run(
    "What is 2 * 3?"
):
    if chunk["tool_calls"]:
        tool_call = chunk['tool_calls']
        print(f"[TOOL CALL] {tool_call['tool_name']} - {tool_call['tool_kwargs']} ")
    elif chunk["delta_content"]:
        print(chunk["delta_content"], end="")
        
