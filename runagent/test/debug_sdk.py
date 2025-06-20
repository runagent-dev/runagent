from runagent import RunAgent

def debug_agent_issue():
    """Debug the agent execution issue"""
    
    print("🔍 DEBUGGING AGENT EXECUTION ISSUE")
    print("=" * 50)
    
    sdk = RunAgent()
    agent_id = "1208924a"
    
    # 1. Check if agent exists
    print("1. Checking agent info...")
    agent_info = sdk.get_agent_info(agent_id)
    if agent_info.get('success'):
        info = agent_info['agent_info']
        print(f"   ✅ Agent found: {agent_id}")
        print(f"   📊 Status: {info.get('status')}")
        print(f"   🔧 Framework: {info.get('framework')}")
        print(f"   📁 Deployment exists: {info.get('deployment_exists')}")
        print(f"   📄 Source exists: {info.get('source_exists')}")
        print(f"   📈 Success rate: {info.get('stats', {}).get('success_rate', 0)}%")
    else:
        print(f"   ❌ Agent not found: {agent_info.get('error')}")
        return
    
    # 2. Try direct execution (bypass HTTP)
    print("\n2. Testing direct execution (bypass HTTP server)...")
    try:
        result = sdk.run_local_agent_direct(agent_id, {
            "messages": [{"role": "user", "content": "test direct"}]
        })
        print(f"   📤 Direct result: {result}")
        
        if result.get('success'):
            print("   ✅ Direct execution works!")
        else:
            print(f"   ❌ Direct execution failed: {result.get('error')}")
            if result.get('traceback'):
                print(f"   📋 Traceback: {result.get('traceback')}")
    except Exception as e:
        print(f"   ❌ Direct execution exception: {e}")
    
    # 3. Try HTTP execution
    print("\n3. Testing HTTP execution (via server)...")
    try:
        result = sdk.run_local_agent(agent_id, {
            "messages": [{"role": "user", "content": "test http"}]
        })
        print(f"   📤 HTTP result: {result}")
        
        if result.get('success'):
            print("   ✅ HTTP execution works!")
        else:
            print(f"   ❌ HTTP execution failed: {result.get('error')}")
            suggestions = result.get('suggestions', [])
            if suggestions:
                print("   💡 Suggestions:")
                for suggestion in suggestions:
                    print(f"      - {suggestion}")
    except Exception as e:
        print(f"   ❌ HTTP execution exception: {e}")
    
    # 4. Use debug method
    print("\n4. Running debug analysis...")
    debug_info = sdk.debug_agent(agent_id)
    print(f"   🔍 Debug info: {debug_info}")
    
    # 5. Check server status
    print("\n5. Checking server status...")
    server_status = sdk.local.check_server_status()
    print(f"   🌐 Server running: {server_status.get('running')}")
    if not server_status.get('running'):
        print(f"   ❌ Server error: {server_status.get('error')}")
    
    print("\n" + "=" * 50)
    print("🔍 Debug complete!")


if __name__ == "__main__":
    debug_agent_issue()