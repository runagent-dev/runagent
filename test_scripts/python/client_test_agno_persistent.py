from runagent import RunAgentClient

# Test 1: Non-streaming with session management
print("=" * 50)
print("Test 1: Non-streaming with session")
print("=" * 50)

# Create client with persistent storage settings
# user_id and persistent_memory are set at client level for persistent storage
ra = RunAgentClient(
    agent_id="c998c025-4c9f-4466-886e-94345efe654b",
    entrypoint_tag="agno_print_response",
    local=False,
    user_id="khalid",  # User ID for persistent storage (VM-level)
    persistent_memory=True  # Enable persistent storage
)

# First message - creating a new session
# Note: 'user' parameter here is for agent's internal session management (different from user_id)
result = ra.run(
    prompt="why you are so funny?",
    user="khalid",  # Agent's internal user ID for session management
    # session_id="01136b0e-6a8f-45f8-8314-fb9a8308872d",
    new_session=False)

print(f"Session ID: {result['session_id']}")
print(f"User ID: {result['user_id']}")
print(f"Response: {result['content']}\n")