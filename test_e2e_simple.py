#!/usr/bin/env python3
"""
Simple E2E Test for Goblin Assistant
Tests basic connectivity and functionality without Playwright
"""

import requests
import time
import sys
import os

# Get port from environment or default
WEB_PORT = int(os.getenv('VITE_PORT', '1420'))

def test_fastapi_endpoints():
    """Test FastAPI backend endpoints"""
    print("Testing FastAPI backend...")

    try:
        # Test providers endpoint
        response = requests.get("http://localhost:3001/providers", timeout=5)
        if response.status_code == 200:
            providers = response.json()
            print(f"✅ Providers endpoint: {len(providers)} providers available")
        else:
            print(f"❌ Providers endpoint failed: {response.status_code}")
            return False

        # Test parse endpoint
        test_orchestration = "test: do something"
        response = requests.post(
            "http://localhost:3001/parse",
            json={"orchestration": test_orchestration},
            timeout=5
        )
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Parse endpoint: orchestration parsed successfully")
        else:
            print(f"❌ Parse endpoint failed: {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ FastAPI connection failed: {e}")
        return False

    return True

def test_web_server():
    """Test web server connectivity"""
    print("Testing web server...")

    try:
        response = requests.get(f"http://localhost:{WEB_PORT}/", timeout=5)
        if response.status_code == 200:
            print(f"✅ Web server: responding on port {WEB_PORT}")
            return True
        else:
            print(f"❌ Web server failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Web server connection failed: {e}")
        return False

def main():
    print("🧪 Goblin Assistant E2E Test Suite")
    print("=" * 40)

    # Test FastAPI
    fastapi_ok = test_fastapi_endpoints()
    print()

    # Test Web Server
    web_ok = test_web_server()
    print()

    # Summary
    print("=" * 40)
    if fastapi_ok and web_ok:
        print("🎉 All tests passed! End-to-end functionality verified.")
        return 0
    else:
        print("❌ Some tests failed. Check server status.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
