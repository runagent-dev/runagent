from runagent import RunAgentClient
import time

# Configuration
AGENT_ID = "f5dd61ef-578c-4a92-abe0-f967b7602738"  # Replace with your deployed agent ID
LOCAL_MODE = False  # Set to True for local testing
USER_ID = "prv"  # RunAgent's persistent storage user ID

print("="*70)
print("LangGraph Chatbot Test Suite")
print("="*70)

# Initialize clients for different entrypoints
chat_client = RunAgentClient(
    agent_id=AGENT_ID,
    entrypoint_tag="chat",
    local=LOCAL_MODE,
    user_id=USER_ID,
    persistent_memory=True
)

stream_client = RunAgentClient(
    agent_id=AGENT_ID,
    entrypoint_tag="chat_stream",
    local=LOCAL_MODE,
    user_id=USER_ID,
    persistent_memory=True
)

history_client = RunAgentClient(
    agent_id=AGENT_ID,
    entrypoint_tag="get_history",
    local=LOCAL_MODE,
    user_id=USER_ID,
    persistent_memory=True
)

threads_client = RunAgentClient(
    agent_id=AGENT_ID,
    entrypoint_tag="list_threads",
    local=LOCAL_MODE,
    user_id=USER_ID,
    persistent_memory=True
)


def test_basic_conversation():
    """Test basic non-streaming conversation with memory."""
    
    # First message
    result = chat_client.run(
        message="who am I and what my father do?",
        user_id=USER_ID,
        thread_id="conversation_001"
    )
    print(f"[Assistant]: {result['response']}")
    print(f"[Info] Thread: {result['thread_id']}, Messages: {result['message_count']}")
    

def test_streaming():
    """Test streaming conversation."""
    print("\n" + "="*70)
    print("TEST 2: Streaming Response (Thread: conversation_001)")
    print("="*70)
    
    print("[Assistant]: ", end='', flush=True)
    
    for chunk in stream_client.run(
        message="can you tell me a long story about xiaomi?",
        user_id=USER_ID,
        thread_id="conversation_001"
    ):
        if chunk.get('type') == 'content':
            print(chunk['content'], end='', flush=True)
        elif chunk.get('type') == 'complete':
            print(f"\n[Info] Thread: {chunk['thread_id']}")


def test_multiple_threads():
    """Test multiple conversation threads."""
    print("\n" + "="*70)
    print("TEST 3: Multiple Threads (Thread isolation)")
    print("="*70)
    
    # Thread 1: Personal chat
    print("\n--- Thread: personal ---")
    print("[User]: I'm planning a vacation to Japan")
    result = chat_client.run(
        message="I'm planning a vacation to Japan",
        user_id=USER_ID,
        thread_id="personal"
    )
    print(f"[Assistant]: {result['response']}")
    
    time.sleep(1)
    
    # Thread 2: Work chat
    print("\n--- Thread: work ---")
    print("[User]: I need to debug a Python function")
    result = chat_client.run(
        message="I need to debug a Python function",
        user_id=USER_ID,
        thread_id="work"
    )
    print(f"[Assistant]: {result['response']}")
    
    time.sleep(1)
    
    # Back to Thread 1 - should remember vacation
    print("\n--- Thread: personal (continued) ---")
    print("[User]: Where was I planning to go?")
    result = chat_client.run(
        message="Where was I planning to go?",
        user_id=USER_ID,
        thread_id="personal"
    )
    print(f"[Assistant]: {result['response']}")
    
    time.sleep(1)
    
    # Thread 2 - should NOT know about vacation
    print("\n--- Thread: work (continued) ---")
    print("[User]: Where was I planning to go?")
    result = chat_client.run(
        message="Where was I planning to go?",
        user_id=USER_ID,
        thread_id="work"
    )
    print(f"[Assistant]: {result['response']}")


def test_conversation_history():
    """Test retrieving conversation history."""
    print("\n" + "="*70)
    print("TEST 4: Conversation History Retrieval")
    print("="*70)
    
    print("\nRetrieving history for thread: conversation_001")
    result = history_client.run(
        user_id=USER_ID,
        thread_id="conversation_001"
    )
    print(result)


def test_list_threads():
    """Test listing all user threads."""
    print("\n" + "="*70)
    print("TEST 5: List All User Threads")
    print("="*70)
    
    result = threads_client.run(user_id=USER_ID)
    
    if result['status'] == 'success':
        print(f"\nUser '{result['user_id']}' has {result['thread_count']} conversation(s):")
        for thread in result['threads']:
            print(f"  - {thread}")
    else:
        print(f"Error: {result.get('message')}")


def test_persistence_across_sessions():
    """Test that conversation persists (simulates app restart)."""
    print("\n" + "="*70)
    print("TEST 6: Persistence Test (Simulated Restart)")
    print("="*70)
    
    print("\nCreating a new client (simulates app restart)...")
    
    # Create a completely new client
    new_client = RunAgentClient(
        agent_id=AGENT_ID,
        entrypoint_tag="chat",
        local=LOCAL_MODE,
        user_id=USER_ID,
        persistent_memory=True
    )
    
    # Try to continue old conversation
    print("\n[User]: What was my name again? (from earlier conversation)")
    result = new_client.run(
        message="What was my name again?",
        user_id=USER_ID,
        thread_id="conversation_001"  # Same thread from test 1
    )
    print(f"[Assistant]: {result['response']}")
    print(f"\n✓ Conversation persisted! The agent remembered from {result['message_count']} messages.")


if __name__ == "__main__":
    try:
        # Run all tests
        # test_basic_conversation()
        # time.sleep(2)
        
        # test_streaming()
        # time.sleep(2)
        
        # test_multiple_threads()
        # time.sleep(2)
        
        test_conversation_history()
        time.sleep(2)
        
        # test_list_threads()
        # time.sleep(2)
        
        # test_persistence_across_sessions()
        
        print("\n" + "="*70)
        print("All tests completed successfully!")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()