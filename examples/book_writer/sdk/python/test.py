from runagent import RunAgentClient

client = RunAgentClient(
    agent_id="a4fa94f2-13e4-4cdf-8f61-647ac611a3a8",
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