"""
Minimal RunAgent SDK Test for TripGenius

Update AGENT_ID and run!

Run from repo root with venv activated:
  pip install -e .
  python examples/trip_planner/sdk/python/test.py
"""

from runagent import RunAgentClient

# UPDATE THIS!
AGENT_ID = "9cc76f5d-9524-4614-b283-d9a50db137b8"


# ============================================
# NON-STREAMING TEST
# ============================================

print("\n🧪 Test 1: Non-Streaming")
print("-" * 50)

client = RunAgentClient(
    agent_id=AGENT_ID,
    entrypoint_tag="trip_create",
    local=False
)

result = client.run(
    destination="Kanazawa",
    num_days=2,
    preferences="Cuisine, Landscape"
)

print(f"\n✅ Result:")
print(result)


# ============================================
# STREAMING TEST
# ============================================

# print("\n\n🧪 Test 2: Streaming")
# print("-" * 50)

# stream_client = RunAgentClient(
#     agent_id=AGENT_ID,
#     entrypoint_tag="trip_stream",
#     local=False
# )

# print("\n📡 Streaming response:\n")

# for chunk in stream_client.run(
#     destination="Paris",
#     num_days=2,
#     preferences="art museums, French cuisine"
# ):
#     print(chunk, end="", flush=True)

# print("\n\n✅ Done!")