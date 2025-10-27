from runagent import RunAgentClient

client = RunAgentClient(
    agent_id="0ce78865-74b7-4b97-91d9-03139e6c0c90",
    entrypoint_tag="generate_outline",
    local=False
)

# result = client.run(
#     title="Introduction to Python",
#     topic="Python programming basics",
#     goal="Teach beginners fundamental Python concepts",
#     num_chapters=3
# )

result = client.run(
    title="Introduction to Python",
    topic="Python programming basics",
    goal="Teach beginners fundamental Python concepts"
)

print(result)