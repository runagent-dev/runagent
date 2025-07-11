from runagent import RunAgentClient
client = RunAgentClient(agent_id="d997a7bb-4f0c-4699-a003-28282de4328a", entrypoint_tag="basic", local=True)
response = client.run({"messages": [{"role": "user", "content": "HI I am radeen and i am sad. What should I do?"}]})
print(response)



####### Iterate over the stream
# for chunk in client.run({"messages": [{"role": "user", "content": "HI I am radeen and i am sad. What should I do?"}]}):
#     print(chunk)