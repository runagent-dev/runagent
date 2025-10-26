from runagent import RunAgentClient

client = RunAgentClient(
    agent_id="dd520db6-5ff6-4b2b-9eea-e3c50453b4d9",
    entrypoint_tag="lead_score_flow",
    local=True
)

result = client.run(
    top_n=1,
    generate_emails=True
)

print(result)