#!/usr/bin/env python3
"""
Minimal test for OpenAI API keys.
"""

import os
import sys
from pathlib import Path


def test_api_keys():
    """Test that API keys are loaded correctly."""
    # Load environment variables from .env
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value

    print("🧪 Testing API key loading...")

    # Check if keys are loaded
    openai_key = os.getenv("OPENAI_API_KEY")
    admin_key = os.getenv("OPENAI_ADMIN_KEY")
    service_key = os.getenv("OPENAI_SERVICE_KEY")

    if openai_key:
        print(f"✅ OPENAI_API_KEY loaded: {openai_key[:20]}...")
    else:
        print("❌ OPENAI_API_KEY not found")
        return False

    if admin_key:
        print(f"✅ OPENAI_ADMIN_KEY loaded: {admin_key[:20]}...")
    else:
        print("⚠️  OPENAI_ADMIN_KEY not found")

    if service_key:
        print(f"✅ OPENAI_SERVICE_KEY loaded: {service_key[:20]}...")
    else:
        print("⚠️  OPENAI_SERVICE_KEY not found")

    # Try a simple API call with requests (avoiding httpx issues)
    try:
        import requests

        headers = {
            "Authorization": f"Bearer {openai_key}",
            "Content-Type": "application/json",
        }

        # Simple models list call
        response = requests.get(
            "https://api.openai.com/v1/models", headers=headers, timeout=10
        )

        if response.status_code == 200:
            print("✅ OpenAI API key is valid - authentication successful")
            return True
        else:
            print(
                f"❌ OpenAI API authentication failed: {response.status_code} - {response.text}"
            )
            return False

    except ImportError:
        print("⚠️  requests not available, skipping API test")
        print("✅ API keys loaded successfully (basic test)")
        return True
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_api_keys()
    sys.exit(0 if success else 1)
