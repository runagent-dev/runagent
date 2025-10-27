# For Python SDK usage:
from runagent import RunAgentClient

client = RunAgentClient(
    agent_id="340f6aeb-0298-49d9-919c-8817756d3f84",
    entrypoint_tag="lead_score_flow",
    local=False
)

result = client.run(
    top_n=1.0,
    generate_emails="true"
)

print(result)

# For CLI usage, run this command:
# runagent run --id 4914e19d-23bc-48c7-ab38-229a14e7eb7a --tag lead_score_flow --top_n=1 --generate_emails=true