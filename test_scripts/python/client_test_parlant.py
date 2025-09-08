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
    message="can you tell me a joke."
)

print("✅ Simple Chat Response:")
print(simple_result)



# ============================================
# STREAMING TESTS
# ============================================

print("\n\n🌊 Testing Parlant Agent - Streaming")
print("=" * 50)


print("\n5️⃣ Testing Streaming Chat")
print("-" * 30)

ra_stream = RunAgentClient(
    agent_id="9c39620c-c309-4478-a44e-2a45e254a9fb",  # Replace with actual agent ID
    entrypoint_tag="parlant_stream",
    local=True
)

print("✅ Streaming Response:")
for chunk in ra_stream.run(
    message="what is the current time now?"
):
    print(chunk)

