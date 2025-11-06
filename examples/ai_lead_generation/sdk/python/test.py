from runagent import RunAgentClient

client = RunAgentClient(
    agent_id="bb9bc13a-ced7-4ac7-a350-a101744109ec",
    entrypoint_tag="generate_leads",
    local=False
)

result = client.run(
    search_query="Ai powered car sell automation",
    num_links=3
)

print(result)