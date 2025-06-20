import requests
import json

def test_http_response():
    """Test the HTTP response format directly"""
    
    print("🧪 TESTING HTTP RESPONSE FORMAT")
    print("=" * 50)
    
    url = "http://127.0.0.1:8450/agents/1208924a/run"
    
    input_data = {
        "messages": [{"role": "user", "content": "test http format"}]
    }
    
    print(f"📤 Sending request to: {url}")
    print(f"📋 Input data: {json.dumps(input_data, indent=2)}")
    
    try:
        response = requests.post(
            url,
            json=input_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"\n📥 Response status: {response.status_code}")
        print(f"📥 Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"📥 Response JSON (formatted):")
            print(json.dumps(result, indent=2))
            
            # Analyze the response structure
            print(f"\n🔍 Response Analysis:")
            print(f"   - Type: {type(result)}")
            print(f"   - Keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            
            if isinstance(result, dict):
                print(f"   - success: {result.get('success')} ({type(result.get('success'))})")
                print(f"   - result: {type(result.get('result'))}")
                print(f"   - error: {result.get('error')} ({type(result.get('error'))})")
                print(f"   - agent_id: {result.get('agent_id')}")
                
                if result.get('result'):
                    result_content = result['result']
                    print(f"   - result.type: {result_content.get('type')}")
                    print(f"   - result.content: {result_content.get('content', '')[:100]}...")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"📋 Response text: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed. Is the server running?")
        print("💡 Start server with: runagent serve")
    except Exception as e:
        print(f"❌ Request failed: {e}")


if __name__ == "__main__":
    test_http_response()