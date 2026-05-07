#!/usr/bin/env python3
"""
Direct test of SiliconeFlow API with debugging.
"""

import os
import sys
import httpx
import asyncio
import time

# Load environment
try:
    from dotenv import load_dotenv

    load_dotenv(".env.local")
    print("✅ Loaded .env.local")
except:
    print("⚠️  Could not load .env.local")

# Get API key
api_key = os.getenv("SILICONEFLOW_API_KEY", "")
print(
    f"\n🔑 API Key from environment: {api_key[:15]}...{api_key[-4:] if len(api_key) > 4 else ''}"
)
print(f"   Length: {len(api_key)} characters")
print(f"   Starts with 'sk-': {api_key.startswith('sk-')}")

if not api_key or api_key == "your_siliconeflow_key_here":
    print("\n❌ API key not properly configured!")
    sys.exit(1)


# Test direct API call
async def test_direct_call():
    """Test direct API call to SiliconeFlow."""

    url = "https://api.siliconflow.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "Qwen/Qwen2.5-7B-Instruct",
        "messages": [
            {"role": "user", "content": "What is 2+2? Answer with just the number."}
        ],
        "max_tokens": 50,
        "temperature": 0.1,
    }

    print(f"\n📡 Making direct API call to: {url}")
    print(f"   Model: {payload['model']}")
    print(f"   Prompt: {payload['messages'][0]['content']}")

    try:
        start = time.perf_counter()

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)

        elapsed_ms = (time.perf_counter() - start) * 1000

        print(f"\n✅ Response Status: {response.status_code}")
        print(f"   Latency: {elapsed_ms:.2f}ms")

        if response.status_code == 200:
            data = response.json()
            print(f"\n📦 Response Data:")
            print(f"   Model: {data.get('model', 'unknown')}")

            choices = data.get("choices", [])
            if choices:
                text = choices[0].get("message", {}).get("content", "")
                print(f"   Response: '{text}'")
                print(f"\n✅ SiliconeFlow API is working!")
                return True
            else:
                print(f"   ❌ No choices in response")
                return False
        else:
            print(f"\n❌ API Error:")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return False

    except Exception as e:
        print(f"\n❌ Exception: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


# Test with provider
async def test_with_provider():
    """Test using the provider dispatcher."""

    print("\n" + "=" * 70)
    print("🔧 Testing with Provider Dispatcher")
    print("=" * 70)

    # Add parent directory to path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    try:
        from api.providers.dispatcher import ProviderDispatcher

        dispatcher = ProviderDispatcher()

        # Check config
        config = dispatcher._get_provider_config("siliconeflow")
        print(f"\n📋 Provider Config:")
        print(f"   Endpoint: {config.get('endpoint', 'NOT SET')}")
        print(f"   API Key Env: {config.get('api_key_env', 'NOT SET')}")

        # Get provider
        provider = dispatcher.get_provider("siliconeflow")
        print(f"\n✅ Provider Created: {type(provider).__name__}")
        print(f"   Endpoint: {provider.endpoint}")
        print(f"   API Key Env: {provider.api_key_env}")
        print(f"   API Key Set: {bool(provider.api_key)}")
        if provider.api_key:
            print(f"   API Key: {provider.api_key[:15]}...{provider.api_key[-4:]}")

        # Make request
        print(f"\n📝 Making request through provider...")
        result = await provider.invoke(
            prompt="What is 2+2? Answer with just the number.",
            model="Qwen/Qwen2.5-7B-Instruct",
            stream=False,
            max_tokens=50,
            temperature=0.1,
        )

        if result.get("ok"):
            print(f"✅ Provider Response: '{result.get('text', '')}'")
            print(f"   Latency: {result.get('latency_ms', 0):.2f}ms")
            return True
        else:
            print(f"❌ Provider Error: {result.get('error', 'unknown')}")
            if result.get("details"):
                print(f"   Details: {result.get('details', '')[:200]}")
            return False

    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    print("\n" + "=" * 70)
    print("🧪 SiliconeFlow Direct Test")
    print("=" * 70)

    # Test 1: Direct API call
    direct_ok = await test_direct_call()

    # Test 2: Through provider
    provider_ok = await test_with_provider()

    print("\n" + "=" * 70)
    print("📊 Test Summary")
    print("=" * 70)
    print(f"Direct API Call: {'✅ WORKING' if direct_ok else '❌ FAILED'}")
    print(f"Provider Method: {'✅ WORKING' if provider_ok else '❌ FAILED'}")
    print("=" * 70)

    return direct_ok or provider_ok


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
