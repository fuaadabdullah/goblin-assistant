#!/usr/bin/env python3
"""
Test script for admin endpoints
"""

import pytest
import requests

BASE_URL = "http://localhost:8003"
pytestmark = pytest.mark.skip(
    reason="Manual smoke script; requires live admin server on localhost:8003"
)


def test_endpoint(endpoint, description):
    """Test a single endpoint"""
    print(f"\n🧪 Testing {description}")
    print(f"   Endpoint: {endpoint}")

    try:
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        if response.status_code == 200:
            print(f"   ✅ Success (Status: {response.status_code})")
            try:
                data = response.json()
                print(f"   📊 Response keys: {list(data.keys())}")
                return True
            except Exception:
                print("   ⚠️  Invalid JSON response")
                return False
        else:
            print(f"   ❌ Failed (Status: {response.status_code})")
            return False
    except requests.exceptions.ConnectionError:
        print("   ❌ Connection failed - server may not be running")
        return False
    except requests.exceptions.Timeout:
        print("   ⏰ Timeout - server may be slow")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def main():
    """Test all admin endpoints"""
    print("🚀 Testing Goblin Assistant Admin Endpoints")
    print("=" * 50)

    endpoints = [
        ("/api/v1/health", "System Health"),
        ("/ops/health/summary", "Admin Health Summary"),
        ("/ops/providers/status", "Provider Status Matrix"),
        ("/ops/performance/snapshot", "Performance Snapshot"),
        ("/ops/queues/snapshot", "Task Queue Monitor"),
        ("/ops/circuit-breakers", "Circuit Breaker Status"),
        ("/api/v1/admin/providers/state", "Provider Registry State"),
    ]

    results = []
    for endpoint, description in endpoints:
        success = test_endpoint(endpoint, description)
        results.append((endpoint, success))

    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for endpoint, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status} {endpoint}")

    print(f"\n📈 Overall: {passed}/{total} endpoints working")

    if passed == total:
        print("🎉 All endpoints are working correctly!")
    else:
        print("⚠️  Some endpoints need attention")


if __name__ == "__main__":
    main()
