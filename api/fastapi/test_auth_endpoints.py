#!/usr/bin/env python3
"""
Test script for MCP authentication endpoints.
"""

import os
import sys
import requests
import json
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_auth_endpoints():
    """Test the authentication endpoints."""
    base_url = "http://localhost:8000"

    print("Testing MCP Authentication Endpoints")
    print("=" * 50)

    # Test login endpoint
    print("\n1. Testing login endpoint...")
    login_data = {"username": "admin", "password": "admin123"}

    try:
        response = requests.post(f"{base_url}/auth/login", json=login_data)
        if response.status_code == 200:
            token_data = response.json()
            print("✅ Login successful")
            print(f"   Token: {token_data['access_token'][:50]}...")
            print(f"   Expires in: {token_data['expires_in']} seconds")
            print(f"   User: {token_data['user']}")

            access_token = token_data["access_token"]

            # Test /auth/me endpoint
            print("\n2. Testing /auth/me endpoint...")
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(f"{base_url}/auth/me", headers=headers)
            if response.status_code == 200:
                user_data = response.json()
                print("✅ User info retrieved")
                print(f"   User: {user_data}")
            else:
                print(f"❌ Failed to get user info: {response.status_code}")
                print(f"   Response: {response.text}")

            # Test admin dashboard (should work for admin user)
            print("\n3. Testing admin dashboard...")
            response = requests.get(f"{base_url}/admin/dashboard", headers=headers)
            if response.status_code == 200:
                dashboard_data = response.json()
                print("✅ Admin dashboard accessed")
                print(f"   System status: {dashboard_data['system_status']}")
                print(f"   Providers: {len(dashboard_data['providers'])} providers")
            else:
                print(f"❌ Failed to access admin dashboard: {response.status_code}")
                print(f"   Response: {response.text}")

        else:
            print(f"❌ Login failed: {response.status_code}")
            print(f"   Response: {response.text}")

    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - is the FastAPI server running?")
        print(
            "   Start the server with: cd api/fastapi && source .venv/bin/activate && uvicorn app:app --reload"
        )
        return False

    # Test invalid login
    print("\n4. Testing invalid login...")
    invalid_login = {"username": "invalid", "password": "invalid"}
    response = requests.post(f"{base_url}/auth/login", json=invalid_login)
    if response.status_code == 401:
        print("✅ Invalid login correctly rejected")
    else:
        print(f"❌ Invalid login not rejected: {response.status_code}")

    print("\n" + "=" * 50)
    print("Authentication tests completed!")
    return True


if __name__ == "__main__":
    test_auth_endpoints()
