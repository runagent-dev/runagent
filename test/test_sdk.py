from runagent import RunAgentClient

# Connect to an already deployed agent
client = RunAgentClient(agent_id="d606beb5-a391-409d-9b5d-2adf86842292", local=True)

# Execute with generic interface
result = client.run_generic(
    query="My mobile has green screen", 
    num_solutions=3
)

print(result)