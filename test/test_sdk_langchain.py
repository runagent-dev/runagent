from runagent import RunAgentClient

client = RunAgentClient(agent_id="694624f8-5e66-4f23-b0b7-28d00d75931c", local=True, port=8460)
result = client.run_generic("My mobile has green screen")
print(result)