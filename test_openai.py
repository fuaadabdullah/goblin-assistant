#!/usr/bin/env python3
"""
Simple test for OpenAI provider with API keys.
"""

import os
import sys
from pathlib import Path

# Add the goblinos package to path
sys.path.insert(0, str(Path(__file__).parent))


def test_openai_provider():
    """Test OpenAI provider initialization."""
    from goblinos.providers.openai import OpenAIProvider

    # Load environment variables from .env
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value

    print("🧪 Testing OpenAI provider initialization...")

    try:
        # Test with regular API key
        provider = OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY"))
        print(f"✅ OpenAI provider initialized: {provider.name}")
        print(f"   Model: {provider.model}")
        print(f"   Supports streaming: {provider.supports_streaming}")

        # Test health check
        import asyncio

        result = asyncio.run(provider.health_check())
        print(f"✅ Health check result: {result}")

        return True

    except Exception as e:
        print(f"❌ OpenAI provider test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_openai_provider()
    sys.exit(0 if success else 1)
