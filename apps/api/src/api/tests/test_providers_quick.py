#!/usr/bin/env python3
"""
Quick test script for SiliconeFlow and LlamaCPP providers.
"""

import asyncio
import os
import sys
import httpx
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.providers.dispatcher import ProviderDispatcher


async def test_siliconeflow():
    """Test SiliconeFlow provider."""
    print("\n" + "=" * 70)
    print("🧪 Testing SiliconeFlow Provider")
    print("=" * 70)

    api_key = os.getenv("SILICONEFLOW_API_KEY", "")

    if not api_key:
        print("❌ SILICONEFLOW_API_KEY not found in environment")
        print("   Please add it to your .env.local file")
        return False

    print(f"✅ API Key found: {api_key[:10]}...{api_key[-4:]}")

    try:
        dispatcher = ProviderDispatcher()
        provider = dispatcher.get_provider("siliconeflow")

        print("\n📝 Testing simple inference...")
        print("   Prompt: 'What is 2+2?'")

        start = time.perf_counter()
        result = await provider.invoke(
            prompt="What is 2+2? Answer with just the number.",
            model="Qwen/Qwen2.5-7B-Instruct",
            stream=False,
            max_tokens=50,
            temperature=0.1,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        if result.get("ok"):
            text = result.get("text", "").strip()
            print(f"✅ Response: '{text}'")
            print(f"   Latency: {elapsed_ms:.2f}ms")
            print(f"   Model: {result.get('model', 'unknown')}")
            if result.get("usage"):
                print(f"   Usage: {result.get('usage')}")
            return True
        else:
            error = result.get("error", "unknown")
            details = result.get("details", "")
            print(f"❌ Failed: {error}")
            if details:
                print(f"   Details: {details}")
            return False

    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


async def test_llamacpp_detailed():
    """Detailed test of LlamaCPP GCP endpoint."""
    print("\n" + "=" * 70)
    print("🧪 Testing LlamaCPP GCP Provider (Detailed)")
    print("=" * 70)

    endpoint = os.getenv("LLAMACPP_GCP_URL", "http://34.132.226.143:8000")
    print(f"\n🔗 Endpoint: {endpoint}")

    # Test 1: Basic connectivity
    print("\n1️⃣ Testing basic connectivity...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{endpoint}/", follow_redirects=True)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   Response: {response.text[:200]}")
    except httpx.TimeoutException:
        print("   ❌ Timeout after 5 seconds")
    except httpx.ConnectError:
        print("   ❌ Connection refused")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

    # Test 2: Health endpoint
    print("\n2️⃣ Testing /health endpoint...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{endpoint}/health", follow_redirects=True)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   Response: {response.text}")
    except httpx.TimeoutException:
        print("   ❌ Timeout after 5 seconds")
    except httpx.ConnectError:
        print("   ❌ Connection refused")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

    # Test 3: Models endpoint
    print("\n3️⃣ Testing /v1/models endpoint...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{endpoint}/v1/models", follow_redirects=True)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                models = data.get("data", [])
                print(f"   Found {len(models)} models:")
                for model in models:
                    print(f"      • {model.get('id', 'unknown')}")
    except httpx.TimeoutException:
        print("   ❌ Timeout after 10 seconds")
    except httpx.ConnectError:
        print("   ❌ Connection refused")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

    # Test 4: Chat completion
    print("\n4️⃣ Testing chat completion...")
    try:
        dispatcher = ProviderDispatcher()
        provider = dispatcher.get_provider("llamacpp_gcp")

        print("   Sending request...")
        start = time.perf_counter()
        result = await provider.invoke(
            prompt="Say 'hello'",
            model="qwen2.5-7b-instruct",
            stream=False,
            max_tokens=10,
            temperature=0.1,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        if result.get("ok"):
            text = result.get("text", "").strip()
            print(f"   ✅ Response: '{text}'")
            print(f"   Latency: {elapsed_ms:.2f}ms")
            return True
        else:
            error = result.get("error", "unknown")
            print(f"   ❌ Failed: {error}")
            return False

    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")
        return False


async def diagnose_llamacpp():
    """Diagnose LlamaCPP connectivity issues."""
    print("\n" + "=" * 70)
    print("🔍 LlamaCPP Diagnostics")
    print("=" * 70)

    endpoint = os.getenv("LLAMACPP_GCP_URL", "http://34.132.226.143:8000")

    # Try different paths
    paths = [
        "/",
        "/health",
        "/v1/models",
        "/v1/chat/completions",
        "/completion",
        "/models",
    ]

    print(f"\n🔗 Testing endpoint: {endpoint}")
    print("📋 Trying different paths...\n")

    for path in paths:
        url = f"{endpoint}{path}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                start = time.perf_counter()
                response = await client.get(url, follow_redirects=True)
                elapsed_ms = (time.perf_counter() - start) * 1000

                status_icon = "✅" if 200 <= response.status_code < 300 else "⚠️"
                print(
                    f"{status_icon} {path:30} → {response.status_code} ({elapsed_ms:.0f}ms)"
                )

                if response.status_code == 200 and len(response.text) < 200:
                    print(f"   Response: {response.text}")

        except httpx.TimeoutException:
            print(f"❌ {path:30} → TIMEOUT (>5s)")
        except httpx.ConnectError:
            print(f"❌ {path:30} → CONNECTION REFUSED")
        except Exception as e:
            print(f"❌ {path:30} → {str(e)[:50]}")

    # Try with curl-like headers
    print("\n📋 Trying with proper headers...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            response = await client.get(
                f"{endpoint}/health", headers=headers, follow_redirects=True
            )
            print(f"✅ With headers: {response.status_code}")
    except Exception as e:
        print(f"❌ With headers: {str(e)[:50]}")


async def main():
    """Main test runner."""
    print("\n" + "=" * 70)
    print("🚀 SiliconeFlow & LlamaCPP Test Suite")
    print("=" * 70)

    # Load environment from .env.local if it exists
    try:
        from dotenv import load_dotenv

        if os.path.exists(".env.local"):
            load_dotenv(".env.local")
            print("✅ Loaded .env.local")
    except ImportError:
        print("⚠️  python-dotenv not installed, using system environment")

    # Test SiliconeFlow
    siliconeflow_ok = await test_siliconeflow()

    # Test LlamaCPP with detailed diagnostics
    llamacpp_ok = await test_llamacpp_detailed()

    # Additional diagnostics for LlamaCPP
    await diagnose_llamacpp()

    # Summary
    print("\n" + "=" * 70)
    print("📊 Test Summary")
    print("=" * 70)
    print(f"SiliconeFlow: {'✅ WORKING' if siliconeflow_ok else '❌ FAILED'}")
    print(f"LlamaCPP GCP: {'✅ WORKING' if llamacpp_ok else '❌ FAILED'}")

    if not siliconeflow_ok:
        print("\n💡 SiliconeFlow Troubleshooting:")
        print("   1. Verify API key in .env.local: SILICONEFLOW_API_KEY=...")
        print("   2. Check key is valid at https://siliconflow.cn")
        print("   3. Restart terminal to reload environment")

    if not llamacpp_ok:
        print("\n💡 LlamaCPP Troubleshooting:")
        print("   1. Check if server is running: ssh to 34.132.226.143")
        print("   2. Verify port 8000 is open: telnet 34.132.226.143 8000")
        print("   3. Check firewall rules on GCP")
        print("   4. Try alternative endpoint if available")

    print("=" * 70)

    return siliconeflow_ok or llamacpp_ok


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
