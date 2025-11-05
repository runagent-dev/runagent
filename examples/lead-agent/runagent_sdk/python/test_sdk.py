# For Python SDK usage:
from runagent import RunAgentClient

client = RunAgentClient(
    agent_id="48d831b5-b090-40ae-bef3-83ba5be61583",
    entrypoint_tag="lead_score_flow",
    local=False
)

# result = client.run(
#     top_n="1",
#     generate_emails="true"
# )

result = client.run(
    top_n=1,
    generate_emails=True
)

print(result)

# For CLI usage, run this command:
# runagent run --id a466eb9a-c0d3-4ede-8200-cb5278364c0e --tag lead_score_flow --top_n=1 --generate_emails=true