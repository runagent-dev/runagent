import sys
import time
import json
from runagent import RunAgentClient

def main():
    if len(sys.argv) != 5:
        print("Usage: python3 agent_test.py <agent_id> <host> <port> <test_message>")
        print("Example: python3 agent_test.py abc123 localhost 8450 'Hello'")
        sys.exit(1)
    
    agent_id = sys.argv[1]
    host = sys.argv[2] 
    port = int(sys.argv[3])
    test_message = sys.argv[4]
    
    print(f"Testing Agent: {agent_id}")
    print(f"Connection: {host}:{port}")
    print(f"Test Message: {test_message}")
    print(f"Framework: langgraph")
    print("=" * 60)
    
    # Prepare input data based on agent configuration
    input_data = {}
    input_data["topic"] = test_message
    input_data["research_question"] = "default"
    input_data["depth"] = "default"
    input_data["sources"] = []
    input_data["citation_style"] = "default"
    input_data["sections"] = []
    input_data["audience"] = "default"
    input_data["max_words"] = 1
    input_data["include_abstract"] = True
    input_data["deadline"] = "default"
    
    print(f"Prepared inputs for agent: {json.dumps(input_data, indent=2)}")
    print(f"Connecting to service at {host}:{port} ...")
    
    # Test each entrypoint tag in order
    entrypoints = ['main', 'main_stream']
    
    for i, tag in enumerate(entrypoints, 1):
        try:
            print(f"\nAttempt {i}/{len(entrypoints)}: Testing entrypoint '{tag}'")
            start_time = time.time()
            
            # Create RunAgentClient
            ra = RunAgentClient(
                agent_id=agent_id,
                entrypoint_tag=tag,
                local=True
            )
            
            print(f"Client created successfully")
            
            # Test the agent
            if "stream" in tag.lower():
                print("Testing streaming mode:")
                print("-" * 40)
                chunk_count = 0
                
                try:
                    for chunk in ra.run(**input_data):
                        chunk_count += 1
                        print(chunk)
                        
                        if chunk_count > 100:  # Prevent infinite loops
                            print("\n... [truncated after 100 chunks]")
                            break
                            
                except Exception as stream_error:
                    print(f"\nStreaming error: {stream_error}")
                    continue
                    
                print(f"\n-" * 40)
                print(f"Received {chunk_count} chunks")
            else:
                print("Testing synchronous mode:")
                result = ra.run(**input_data)
                print(f"Result Type: {type(result)}")
                print(f"Result Content:")
                if isinstance(result, dict):
                    if 'content' in result:
                        print(result['content'])
                    else:
                        print(json.dumps(result, indent=2, default=str))
                else:
                    result_str = str(result)
                    print(result_str[:500] + "..." if len(result_str) > 500 else result_str)
            
            elapsed = time.time() - start_time
            print(f"\nExecution Time: {elapsed:.2f} seconds")
            print(f"SUCCESS! Agent responded via entrypoint '{tag}'")
            sys.exit(0)
            
        except Exception as e:
            print(f"Failed with entrypoint '{tag}': {str(e)}")
            if i < len(entrypoints):
                print("Trying next entrypoint...")
            continue
    
    print(f"\nAll {len(entrypoints)} entrypoints failed!")
    print("Troubleshooting tips:")
    print("   - Verify the agent is running at the specified host:port")
    print("   - Check that agent_id is correct")
    print("   - Ensure RunAgent is installed: pip install runagent")
    print("   - Try different entrypoint tags manually")
    sys.exit(1)

if __name__ == "__main__":
    main()
