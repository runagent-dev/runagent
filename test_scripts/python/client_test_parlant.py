# test_scripts/python/client_test_parlant.py

from runagent import RunAgentClient

# ============================================
# NON-STREAMING TESTS
# ============================================

print("🧪 Testing Parlant Agent - Non-Streaming")
print("=" * 50)

# Test 1: Simple Chat
print("\n1️⃣ Testing Simple Chat")
print("-" * 30)

ra_simple = RunAgentClient(
    agent_id="9c39620c-c309-4478-a44e-2a45e254a9fb",  # Replace with actual agent ID
    entrypoint_tag="parlant_simple",
    local=True
)

simple_result = ra_simple.run(
    message="What's the weather like in Paris?"
)

print("✅ Simple Chat Response:")
print(simple_result)

# # Test 2: Conversational Chat with Session
# print("\n2️⃣ Testing Conversational Chat")
# print("-" * 30)

# ra_conversation = RunAgentClient(
#     agent_id="your-parlant-agent-id-here",  # Replace with actual agent ID
#     entrypoint_tag="parlant_conversation",
#     local=True
# )

# conversation_result = ra_conversation.run(
#     message="Hello! I need help with something.",
#     session_id="test-session-123"
# )

# print("✅ Conversational Response:")
# print(conversation_result)

# # Test 3: Custom Guidelines
# print("\n3️⃣ Testing Custom Guidelines")
# print("-" * 30)

# ra_custom = RunAgentClient(
#     agent_id="your-parlant-agent-id-here",  # Replace with actual agent ID
#     entrypoint_tag="parlant_custom",
#     local=True
# )

# custom_guidelines = [
#     {
#         "condition": "User asks about pricing",
#         "action": "Politely explain that pricing information is available on our website"
#     },
#     {
#         "condition": "User mentions support",
#         "action": "Direct them to our support team with contact information"
#     }
# ]

# custom_result = ra_custom.run(
#     message="How much does your service cost?",
#     guidelines=custom_guidelines
# )

# print("✅ Custom Guidelines Response:")
# print(custom_result)

# # Test 4: Agent Info
# print("\n4️⃣ Testing Agent Info")
# print("-" * 30)

# ra_info = RunAgentClient(
#     agent_id="your-parlant-agent-id-here",  # Replace with actual agent ID
#     entrypoint_tag="parlant_info",
#     local=True
# )

# info_result = ra_info.run()

# print("✅ Agent Info:")
# print(info_result)

# # ============================================
# # STREAMING TESTS
# # ============================================

# print("\n\n🌊 Testing Parlant Agent - Streaming")
# print("=" * 50)

# # Test 5: Streaming Chat
# print("\n5️⃣ Testing Streaming Chat")
# print("-" * 30)

# ra_stream = RunAgentClient(
#     agent_id="your-parlant-agent-id-here",  # Replace with actual agent ID
#     entrypoint_tag="parlant_stream",
#     local=True
# )

# print("✅ Streaming Response:")
# for chunk in ra_stream.run(
#     message="Tell me a story about a helpful AI assistant"
# ):
#     print(chunk.get('content', chunk), end="")
#     if chunk.get('is_final'):
#         print("\n[Stream Complete]")
#         break

# # Test 6: Weather Tool Usage
# print("\n\n6️⃣ Testing Weather Tool")
# print("-" * 30)

# weather_result = ra_simple.run(
#     message="What's the weather like in Tokyo and London?"
# )

# print("✅ Weather Tool Response:")
# print(weather_result)

# # Test 7: Time Tool Usage
# print("\n7️⃣ Testing Time Tool")
# print("-" * 30)

# time_result = ra_simple.run(
#     message="What time is it right now?"
# )

# print("✅ Time Tool Response:")
# print(time_result)

# print("\n✅ All Parlant tests completed!")