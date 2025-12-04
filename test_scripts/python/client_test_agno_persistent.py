# from runagent import RunAgentClient

# # Test 1: Non-streaming with session management
# print("=" * 50)
# print("Test 1: Non-streaming with session")
# print("=" * 50)

# # Create client with persistent storage settings
# # user_id and persistent_memory are set at client level for persistent storage
# ra = RunAgentClient(
#     agent_id="b298c025-4c9f-4466-886e-14745efe664b",
#     entrypoint_tag="agno_print_response",
#     local=False,
#     user_id="khalid",  # User ID for persistent storage (VM-level)
#     persistent_memory=True  # Enable persistent storage
# )

# # First message - creating a new session
# # Note: 'user' parameter here is for agent's internal session management (different from user_id)
# result = ra.run(
#     prompt="i told you my dream job. please tell me what was it?",
#     user="khalid",  # Agent's internal user ID for session management
#     session_id="fac40913-fb9c-41aa-821d-2bc204f9daf2",
#     new_session=False)

# print(f"Session ID: {result['session_id']}")
# print(f"User ID: {result['user_id']}")
# print(f"Response: {result['content']}\n")



from runagent import RunAgentClient

# Test 1: Non-streaming with session management
print("=" * 50)
print("Test 1: Non-streaming with session")
print("=" * 50)

# Create client with persistent storage settings
# user_id and persistent_memory are set at client level for persistent storage
ra = RunAgentClient(
    agent_id="c778c025-4c9f-4466-886e-14845efe664b",
    entrypoint_tag="agno_print_response",
    local=False,
    user_id="prova",  # User ID for persistent storage (VM-level)
    persistent_memory=True  # Enable persistent storage
)

# First message - creating a new session
# Note: 'user' parameter here is for agent's internal session management (different from user_id)
result = ra.run(
    prompt="can you tell me my favorite movie and tv series? I told you before. I told you both.",
    user="prova",  # Agent's internal user ID for session management
    # session_id="ccb19879-5416-4715-96d3-f62036ccf429",
    session_id="f927c786-87c1-45c4-a201-aaa1711b8f53",
    new_session=False)

print(f"Session ID: {result['session_id']}")
print(f"User ID: {result['user_id']}")
print(f"Response: {result['content']}\n")