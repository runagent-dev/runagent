##non-streaming


# from runagent import RunAgentClient

# ra = RunAgentClient(
#     agent_id="80277adc-77f5-4314-a95d-9bb265bbdda3",
#     entrypoint_tag="ag2_invoke",
#     local=True
#     )


# agent_result = ra.run(
#     message="The solar sytem has 2 planets.",
#     max_turns=3
# )

# print(agent_result)
# ==================================


######streaming

from runagent import RunAgentClient

ra = RunAgentClient(
    agent_id="80277adc-77f5-4314-a95d-9bb265bbdda3",
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
