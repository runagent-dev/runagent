# test_agent_sdk.py
# Run this script to see what the SDK response looks like

from runagent import RunAgentClient
import json

def test_agent(agent_id, port=8450):
    """Test the agent with SDK and show detailed output"""
    
    print(f"🧪 Testing Agent: {agent_id}")
    print(f"🔌 Port: {port}")
    print("=" * 50)
    
    try:
        # Create client - try different entrypoint tags
        entrypoint_tags = ["main", "generic", "basic", "invoke"]
        
        for tag in entrypoint_tags:
            print(f"\n🎯 Trying entrypoint tag: '{tag}'")
            
            try:
                ra = RunAgentClient(
                    agent_id=agent_id,
                    entrypoint_tag=tag,
                    local=True
                )
                
                print(f"✅ Client created successfully with tag: {tag}")
                
                # Test with minimal input
                test_inputs = [
                    {"math_query": "What is 3*3?"}
                ]
                
                for test_input in test_inputs:
                    try:
                        print(f"\n📝 Testing with input: {test_input}")
                        
                        result = ra.run(**test_input)
                        
                        print("✅ SUCCESS!")
                        print(f"📤 Result type: {type(result)}")
                        print(f"📤 Result content:")
                        if isinstance(result, dict):
                            print(json.dumps(result, indent=2))
                        else:
                            print(result)
                        
                        return True  # Success, exit
                        
                    except Exception as input_error:
                        print(f"❌ Input failed: {input_error}")
                        continue
                
            except Exception as tag_error:
                print(f"❌ Tag '{tag}' failed: {tag_error}")
                continue
        
        print("\n❌ All attempts failed")
        return False
        
    except Exception as e:
        print(f"❌ General error: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        agent_id = sys.argv[1]
    else:
        agent_id = input("Enter Agent ID: ").strip()
    
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    else:
        port = 8450
    
    test_agent(agent_id, port)