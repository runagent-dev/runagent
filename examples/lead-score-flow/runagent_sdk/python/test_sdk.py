from runagent import RunAgentClient

client = RunAgentClient(
    agent_id="dbf63fb6-a11c-40a9-aae0-84e57b16ad01",
    entrypoint_tag="lead_score_flow",
    local=True
)

result = client.run(
    top_n=3,
    generate_emails=True
)

print(result)