#!/usr/bin/env python3
"""
Simple test script for auth endpoints
"""

import requests
import time


def test_endpoint(name, method, url, data=None):
    print(f"\n🧪 Testing {name}...")
    try:
        start_time = time.time()
        if method == "POST":
            response = requests.post(url, json=data, timeout=10)
        else:
            response = requests.get(url, timeout=10)

        response_time = time.time() - start_time
        print(f"Status: {response.status_code}")
        print(".3f")
        print(f"Response: {response.text[:200]}...")

        return response.status_code, response_time, response.text
    except Exception as e:
        print(f"Error: {e}")
        return 0, 0, str(e)


if __name__ == "__main__":
    base_url = "http://localhost:8003"

    # Test health endpoint
    test_endpoint("Health", "GET", f"{base_url}/health")

    # Test registration
    test_endpoint(
        "Registration",
        "POST",
        f"{base_url}/auth/register",
        {
            "email": "test@example.com",
            "password": "testpass123",
            "full_name": "Test User",
        },
    )

    # Test login
    test_endpoint(
        "Login",
        "POST",
        f"{base_url}/auth/login",
        {"email": "test@example.com", "password": "testpass123"},
    )
