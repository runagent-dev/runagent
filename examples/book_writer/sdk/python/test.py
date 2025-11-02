from runagent import RunAgentClient

client = RunAgentClient(
    agent_id="111c6b65-058f-4b9d-8e82-8417de7fcc9d",
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