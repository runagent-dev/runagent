from runagent import RunAgentClient
client = RunAgentClient(agent_id="957236a4-8a38-43f8-9133-87083fba5960", entrypoint_tag="basic_stream", local=True)
# response = client.run({"messages": [{"role": "user", "content": "HI I am radeen and i am sad. What should I do?"}]})




####### Iterate over the stream
# for chunk in client.run({"messages": [{"role": "user", "content": "HI I am radeen and i am sad. What should I do?"}]}):
#     print(chunk)