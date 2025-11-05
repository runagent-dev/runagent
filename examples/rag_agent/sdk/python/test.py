from runagent import RunAgentClient

# # Non-streaming client
# client = RunAgentClient(
#     agent_id="5d072242-bb9c-4567-bbdb-432811697060",
#     entrypoint_tag="query",
#     local=True
# )

# result = client.run(
#     question="i am sad. Tell me a joke."
# )

# print("=== Non-Streaming Result ===")
# print(result["answer"])
# print(f"Source: {result['source']}")
# print(f"Database: {result['database_used']}")

# Streaming client
print("\n=== Streaming Result ===")
streaming_client = RunAgentClient(
    agent_id="5d072242-bb9c-4567-bbdb-432811697060",
    entrypoint_tag="query_stream",
    local=True
)

# Stream the response
stream = streaming_client.run_stream(
    question="What is Nvidia's  price-to-sales (P/S) ratio according to the document? And also the cash flow analysis in the document?"
)

metadata = None
full_answer = ""
for chunk in stream:
    if chunk.get("type") == "metadata":
        metadata = chunk
        print(f"Source: {chunk.get('source')}")
        print(f"Database: {chunk.get('database_used')}")
        print("Answer (streaming): ", end="", flush=True)
    elif chunk.get("type") == "content":
        content = chunk.get("content", "")
        print(content, end="", flush=True)
        full_answer += content
    elif chunk.get("type") == "complete":
        print(f"\n\nStreaming complete! Total length: {chunk.get('total_length')} characters")
    elif chunk.get("type") == "error":
        print(f"\nError: {chunk.get('error')}")