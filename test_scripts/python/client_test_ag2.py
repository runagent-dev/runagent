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
    agent_id="338d629e-53b4-46cb-a6d9-9db1b5b5c5c8",
    entrypoint_tag="ag2_stream",
    local=True
    )

# print(ra.run(message="The water is blue.", max_turns=3))

for chunk in ra.run(
    message="Man breathe oxygen.",
    max_turns=3
):
    print(f"{chunk['sender']}: {chunk['content']}")
    print("-------")
