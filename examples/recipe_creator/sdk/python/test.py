"""
Simple test script for ChefGenius Recipe Agent using RunAgent Python SDK

Usage:
    python test_agent.py
"""

from runagent import RunAgentClient
from dotenv import load_dotenv
import os




print("🧪 Testing ChefGenius Recipe Agent")
print("=" * 50)

# Test 1: Non-streaming recipe creation
def test_non_streaming():
    print("\n1️⃣ Test: Non-Streaming Recipe Creation")
    print("-" * 50)
    
    client = RunAgentClient(
        agent_id="9cd7f85d-248c-4931-831a-5b4d43a01a78",
        entrypoint_tag="recipe_create",
        local=False
    )
    
    result = client.run(
        ingredients="chicken breast, broccoli, rice, garlic",
        dietary_restrictions="",
        time_limit="30 minutes"
    )
    
    print("✅ Result:")
    if result.get("success"):
        print(result["recipe"])
    else:
        print("❌ Error:", result)
    
    return result


# Test 2: Streaming recipe creation
def test_streaming():
    print("\n2️⃣ Test: Streaming Recipe Creation")
    print("-" * 50)
    
    client = RunAgentClient(
        agent_id="9cd7f85d-248c-4931-831a-5b4d43a01a78",
        entrypoint_tag="recipe_stream",
        local=False
    )
    
    print("✅ Streaming output:\n")
    
    for chunk in client.run(
        ingredients="pasta, mushrooms, spinach, cream",
        dietary_restrictions="vegetarian",
        time_limit="25 minutes"
    ):
        print(chunk)
    
    print("\n\n✅ Stream complete!")


# Test 3: Quick test with minimal params
def test_quick():
    print("\n3️⃣ Test: Quick Recipe (minimal params)")
    print("-" * 50)
    
    client = RunAgentClient(
        agent_id=AGENT_ID,
        entrypoint_tag="recipe_create",
        local=LOCAL_MODE
    )
    
    result = client.run(
        ingredients="eggs, cheese, tomatoes"
    )
    
    print("✅ Result:")
    if result.get("success"):
        print(result["recipe"][:500] + "...")  # Show first 500 chars
    else:
        print("❌ Error:", result)


# Test 4: Vegan recipe
def test_vegan():
    print("\n4️⃣ Test: Vegan Recipe")
    print("-" * 50)
    
    client = RunAgentClient(
        agent_id=AGENT_ID,
        entrypoint_tag="recipe_create",
        local=LOCAL_MODE
    )
    
    result = client.run(
        ingredients="quinoa, chickpeas, sweet potato, kale",
        dietary_restrictions="vegan",
        time_limit="40 minutes"
    )
    
    print("✅ Result:")
    if result.get("success"):
        print(result["recipe"][:500] + "...")
    else:
        print("❌ Error:", result)


# Main test runner
def run_all_tests():
    try:
        # Validate agent ID
        if AGENT_ID == "your-agent-id-here":
            print("❌ ERROR: Please set AGENT_ID in .env file")
            print("   Run 'runagent serve .' in the agent directory first")
            return
        
        print(f"Agent ID: {AGENT_ID}")
        print(f"Local Mode: {LOCAL_MODE}")
        
        # Run tests
        test_non_streaming()
        print("\n" + "=" * 50)
        
        test_streaming()
        print("\n" + "=" * 50)
        
        test_quick()
        print("\n" + "=" * 50)
        
        test_vegan()
        print("\n" + "=" * 50)
        
        print("\n🎉 All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # You can run individual tests or all tests
    
    # Run all tests
    # run_all_tests()
    
    # Or run individual tests:
    # test_non_streaming()
    test_streaming()
    # test_quick()
    # test_vegan()