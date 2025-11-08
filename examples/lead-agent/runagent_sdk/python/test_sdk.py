# For Python SDK usage:
from runagent import RunAgentClient

client = RunAgentClient(
    agent_id="89aef000-0000-0000-0000-000000000000",
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