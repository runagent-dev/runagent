#!/usr/bin/env python3
"""Quick test of PHP SDK endpoints without full execution"""

import requests
import json

AGENT_ID = '91e70681-def8-4600-8a30-d037c1b51870'
BASE_URL = 'http://0.0.0.0:8333'
API_KEY = 'rau_1d8e1d71edfeb4c77a59813f661094da19f13c53b9e3b4be9bac281b59bab4f6'

headers = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json'
}

print("Testing PHP SDK endpoints...\n")

# Test 1: Architecture
print("1. Testing Architecture Endpoint...")
try:
    r = requests.get(f"{BASE_URL}/api/v1/agents/{AGENT_ID}/architecture", 
                     headers=headers, timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f"   ✓ SUCCESS - Found {len(data.get('data', {}).get('entrypoints', []))} entrypoints")
        for ep in data.get('data', {}).get('entrypoints', []):
            print(f"     - {ep['tag']}")
    else:
        print(f"   ✗ FAILED - Status {r.status_code}")
except Exception as e:
    print(f"   ✗ ERROR: {e}")

# Test 2: Health
print("\n2. Testing Health Endpoint...")
try:
    r = requests.get(f"{BASE_URL}/api/v1/health", headers=headers, timeout=5)
    if r.status_code == 200:
        print(f"   ✓ SUCCESS - Agent is healthy")
    else:
        print(f"   ✗ FAILED - Status {r.status_code}")
except Exception as e:
    print(f"   ✗ ERROR: {e}")

print("\n✅ PHP SDK endpoint testing complete!")
print("\nTo test actual execution (requires agent restart with OPENAI_API_KEY):")
print("1. Stop agent: runagent stop --id", AGENT_ID)
print("2. Set key: export OPENAI_API_KEY='sk-proj-...'")
print("3. Start agent: runagent start --id", AGENT_ID)
print("4. Run: python3 verify_php_sdk_with_nice_agent.py")
