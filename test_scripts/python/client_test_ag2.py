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
    agent_id="83138c65-e6b6-4929-a06c-ade7b424a720",
    entrypoint_tag="ag2_invoke",
    local=True
    )

print(ra.run(message="The solar sytem has 2 planets.", max_turns=3))

# for chunk in ra.run(
#     message="The solar sytem has 2 planets.",
#     max_turns=3
# ):
#     print(f"{chunk['sender']}: {chunk['content']}")
#     print("-------")
