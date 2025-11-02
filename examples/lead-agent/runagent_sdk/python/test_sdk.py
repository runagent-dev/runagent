# For Python SDK usage:
from runagent import RunAgentClient

client = RunAgentClient(
    agent_id="706b9423-a817-4953-a899-d2d2404e0799",
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