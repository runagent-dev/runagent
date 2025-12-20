from runagent import RunAgentClient

# ============================================================================
# OPTION 1: Standard synchronous mode (sequential processing)
# ============================================================================
# This is the default mode - processes papers one by one
# Use this if you want simple, straightforward execution
# Note: Update agent_id if you redeployed the agent
# client = RunAgentClient(
#     agent_id="62f7a781-51bb-4d62-a68f-24dc4f2bfd0b",  # Updated to match runagent.config.json
#     entrypoint_tag="check_papers",  # Standard synchronous entrypoint
#     local=False,
#     user_id="prova3",  # User ID for persistent storage (VM-level)
#     persistent_memory=True  # Enable persistent storage
# )
# result = client.run(
#     topics=["reinforcement learning"],
#     max_results=20,
#     days_back=100
# )

# print(f"Found {result['total_relevant']} relevant papers")
# print(f"Email sent: {result['email_sent']}")

# ============================================================================
# OPTION 2: Async/Parallel mode (faster, processes papers in parallel)
# ============================================================================
# Uncomment below to use async mode - processes up to 10 papers simultaneously
# This is much faster for large batches of papers
#
client_async = RunAgentClient(
    agent_id="62f7a781-71bb-4d62-a68f-24dc4f2bfd0b",
    entrypoint_tag="check_papers_async",  # Async entrypoint with parallel processing
    local=False,
    user_id="prova4",
    persistent_memory=True
)
result_async = client_async.run(
    topics=["LLM finetuning"],
    max_results=20,
    days_back=100
)
print(f"Found {result_async['total_relevant']} relevant papers (async mode)")
print(f"Email sent: {result_async['email_sent']}")

# ============================================================================
# OPTION 3: Streaming mode (real-time progress updates)
# ============================================================================
# Uncomment below to use streaming mode - see progress as it happens
# The VM stays alive and streams results in real-time
# Note: Requires SDK support for streaming or use WebSocket endpoint
#
# import asyncio
#
# async def stream_example():
#     client_stream = RunAgentClient(
#         agent_id="62f7a781-51bb-4d62-a68f-24dc4f2bfd0b",
#         entrypoint_tag="check_papers_stream",  # Streaming entrypoint
#         local=False,
#         user_id="prova3",
#         persistent_memory=True
#     )
#     
#     # If SDK supports streaming:
#     # async for update in client_stream.run_stream(
#     #     topics=["reinforcement learning"],
#     #     max_results=20,
#     #     days_back=100
#     # ):
#     #     update_type = update.get("type", "unknown")
#     #     if update_type == "status":
#     #         print(f"📊 {update.get('message', '')} [{update.get('progress', 0)}%]")
#     #     elif update_type == "paper":
#     #         print(f"📄 Found paper: {update.get('paper', '')[:100]}...")
#     #     elif update_type == "complete":
#     #         print(f"✅ Complete: {update.get('total_relevant', 0)} papers found")
#     
#     # Alternative: Use WebSocket endpoint if available
#     # See: /home/azureuser/runagent/test_scripts/python/client_test_paperflow_stream.py
#     # for a complete streaming example
#
# # asyncio.run(stream_example())

# ============================================================================
# QUICK REFERENCE:
# ============================================================================
# - check_papers:        Standard mode (sequential, one paper at a time)
# - check_papers_async:  Fast mode (parallel, up to 10 papers simultaneously)
# - check_papers_stream: Streaming mode (real-time progress, VM stays alive)
#
# For streaming examples, see:
# /home/azureuser/runagent/test_scripts/python/client_test_paperflow_stream.py