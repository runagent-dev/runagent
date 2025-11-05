#!/usr/bin/env python3
"""
Test script to check if backend is accessible
"""
import requests
import sys

def test_backend(url):
    """Test if backend is accessible"""
    print(f"Testing backend at: {url}")
    print("=" * 60)
    
    try:
        # Test health endpoint
        response = requests.get(f"{url}/health", timeout=5)
        print(f"✅ SUCCESS! Backend is accessible")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.json()}")
        return True
    except requests.exceptions.ConnectionError:
        print(f"❌ FAILED: Cannot connect to backend")
        print(f"   Error: Connection refused")
        print(f"   Possible causes:")
        print(f"   1. Backend server is not running")
        print(f"   2. Port 5000 is blocked by firewall")
        print(f"   3. Backend is not listening on the correct interface")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ FAILED: Connection timed out")
        print(f"   The backend is not responding")
        return False
    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}: {str(e)}")
        return False

if __name__ == '__main__':
    # Test localhost
    print("\n1. Testing localhost connection:")
    test_backend("http://localhost:5000")
    
    # Test internal IP
    print("\n2. Testing internal IP (10.1.0.5):")
    test_backend("http://10.1.0.5:5000")
    
    # Test public IP (if accessible)
    print("\n3. Testing public IP (20.84.81.110):")
    test_backend("http://20.84.81.110:5000")
    
    print("\n" + "=" * 60)
    print("If localhost works but public IP doesn't, check:")
    print("1. Firewall/security group allows port 5000")
    print("2. Backend is running with host='0.0.0.0'")
    print("3. Network configuration allows external access")

