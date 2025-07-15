# from runagent import RunAgentClient

# ra = RunAgentClient(
#     agent_id="52f357ae-d4d8-4146-9ea5-8669a6091475",
#     entrypoint_tag="ag2_invoke",
#     local=True
#     )


# agent_result = ra.run(
#     message="The solar sytem has 2 planets.",
#     max_turns=3
# )

# print(agent_result)
# ==================================

from runagent import RunAgentClient

ra = RunAgentClient(
    agent_id="52f357ae-d4d8-4146-9ea5-8669a6091475",
    entrypoint_tag="ag2_stream",
    local=True
    )

for chunk in ra.run(
    message="The solar sytem has 2 planets.",
    max_turns=3
):
    print(f"{chunk['sender']}: {chunk['content']}")
    print("-------")
