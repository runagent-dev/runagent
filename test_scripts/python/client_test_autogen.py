# from runagent import RunAgentClient

# ra = RunAgentClient(
#     agent_id="20cf0046-15f6-4b9e-84b4-9be60c031fdc",
#     entrypoint_tag="autogen_invoke",
#     local=True
# )

# agent_result = ra.run(
#     task="What is Autogen??"
# )
# print(agent_result)
# ==================================

# from runagent import RunAgentClient

# ra = RunAgentClient(
#     agent_id="20cf0046-15f6-4b9e-84b4-9be60c031fdc",
#     entrypoint_tag="autogen_step_stream",
#     local=True
#     )

# for chunk in ra.run(
#     task="Analyze the benefits of remote work for software teams"
# ):
#     if chunk["type"] == "TextMessage":
#         print(f"\n\n{chunk['source']}:")
#         print("=====================")
#         print(chunk["message"])

# ==================================

# from runagent import RunAgentClient

# ra = RunAgentClient(
#     agent_id="20cf0046-15f6-4b9e-84b4-9be60c031fdc",
#     entrypoint_tag="autogen_token_stream",
#     local=True
#     )

# for chunk in ra.run(
#     task="Analyze the benefits of remote work for software teams"
# ):  
#     if chunk["type"] == "ModelClientStreamingChunkEvent":
#         print(chunk["delta"], end="")


