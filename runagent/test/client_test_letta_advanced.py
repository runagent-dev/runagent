from runagent import RunAgentClient

client = RunAgentClient(agent_id="63cd7d3c-439f-4386-92e1-5e8c96f7d108", entrypoint_tag="basic", local=True)

response = client.run("tell me about love and horoscope using rag_tool")

print(response)