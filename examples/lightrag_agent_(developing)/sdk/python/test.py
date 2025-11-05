from runagent import RunAgentClient

# # 1. Initialize (first time only)
# client = RunAgentClient(
#     agent_id="339d8688-c604-4ff4-bd44-d0968dd80cd4",
#     entrypoint_tag="init_agent",
#     local=True
# )
# result = client.run()
# print(result)

## 2. Process documents
# client = RunAgentClient(
#     agent_id="339d8688-c604-4ff4-bd44-d0968dd80cd4",
#     entrypoint_tag="process_multimodal",
#     local=True
# )
# result = client.run(file_path="/home/azureuser/magicmind/document_parse/uploads/gold-mine.png")
# print(result)
# 3. Query
client = RunAgentClient(
    agent_id="339d8688-c604-4ff4-bd44-d0968dd80cd4",
    entrypoint_tag="query",
    local=True
)
answer = client.run(
    query="What is the content of the document?",
    mode="naive"
)
print(answer)
# # 4. Monitor
# client = RunAgentClient(
#     agent_id="your-agent-id",
#     entrypoint_tag="stats",
#     local=True
# )
# stats = client.run()
# print(f"Documents: {stats['stats']['document_count']}")
# print(stats)