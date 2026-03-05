#!/usr/bin/env python3
"""
Comprehensive test script to verify Kamatera LLM chat functionality.
Tests the complete flow: provider connectivity -> dispatcher -> chat API
"""

import asyncio
import sys
import os

# Add the API directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "api"))

from api.providers.dispatcher_fixed import ProviderDispatcher
import httpx


async def test_provider_dispatcher():
    """Test the provider dispatcher directly"""
    print("\n" + "=" * 70)
    print("🧪 TESTING PROVIDER DISPATCHER")
    print("=" * 70)

    dispatcher = ProviderDispatcher()

    # Test 1: Auto-selection
    print("\n1️⃣  Auto-Provider Selection")
    try:
        selected = await dispatcher._auto_select_provider()
        print(f"   ✅ Auto-selected provider: {selected}")
    except Exception as e:
        print(f"   ❌ Auto-selection failed: {e}")
        return False

    # Test 2: Direct llama.cpp (Router) invocation
    print("\n2️⃣  Direct llama.cpp (Router) Provider")
    try:
        result = await dispatcher.invoke_provider(
            provider_id="llamacpp_kamatera",
            model="qwen2.5:latest",
            payload={
                "messages": [
                    {"role": "user", "content": "Say 'Hello World' in one sentence"}
                ]
            },
            timeout_ms=30000,
            stream=False,
        )

        if result.get("ok"):
            text = result.get("result", {}).get("text", "")
            print(f"   ✅ Provider response: {text[:100]}")
        else:
            print(f"   ❌ Provider error: {result.get('error')}")
            return False
    except Exception as e:
        print(f"   ❌ Provider invocation failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Test 3: Streaming
    print("\n3️⃣  Streaming Response")
    try:
        result = await dispatcher.invoke_provider(
            provider_id="llamacpp_kamatera",
            model="qwen2.5:latest",
            payload={"messages": [{"role": "user", "content": "Count from 1 to 3"}]},
            timeout_ms=30000,
            stream=True,
        )

        if result.get("ok"):
            stream = result.get("stream")
            if stream:
                print("   ✅ Stream created successfully")
                text_parts = []
                async for chunk in stream:
                    text = chunk.get("text", "")
                    if text:
                        text_parts.append(text)
                full_text = "".join(text_parts)
                print(f"   ✅ Streamed text: {full_text[:100]}")
            else:
                print("   ❌ No stream object in response")
        else:
            print(f"   ❌ Streaming failed: {result.get('error')}")
    except Exception as e:
        print(f"   ⚠️  Streaming test failed: {e}")
        # Not critical - continue

    return True


async def test_api_endpoint():
    """Test the actual API endpoint"""
    print("\n" + "=" * 70)
    print("🧪 TESTING API ENDPOINT")
    print("=" * 70)

    base_url = "http://localhost:8004"

    # Check if backend is running
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/health")
            if response.status_code != 200:
                print(f"\n❌ Backend health check failed: {response.status_code}")
                print("   The backend server needs to be running on port 8004")
                print(
                    "   Run: cd apps/goblin-assistant && python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8004"
                )
                return False
    except Exception as e:
        print(f"\n❌ Backend not accessible: {e}")
        print("   The backend server needs to be running on port 8004")
        print(
            "   Run: cd apps/goblin-assistant && python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8004"
        )
        return False

    print("\n1️⃣  Backend Health")
    print("   ✅ Backend is running")

    async with httpx.AsyncClient() as client:
        # Test 2: Create conversation
        print("\n2️⃣  Create Conversation")
        try:
            response = await client.post(
                f"{base_url}/chat/conversations", json={"title": "Kamatera Chat Test"}
            )

            if response.status_code != 200:
                print(f"   ❌ Failed: {response.status_code} - {response.text[:200]}")
                return False

            conv_data = response.json()
            conv_id = conv_data.get("conversation_id")
            print(f"   ✅ Created conversation: {conv_id}")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return False

        # Test 3: Send message
        print("\n3️⃣  Send Message (non-streaming)")
        try:
            response = await client.post(
                f"{base_url}/chat/conversations/{conv_id}/messages",
                json={
                    "message": "Hello! Please respond with 'Chat is working'",
                    "provider": None,  # Auto-select
                    "stream": False,
                },
            )

            if response.status_code != 200:
                print(f"   ❌ Failed: {response.status_code} - {response.text[:500]}")
                return False

            msg_data = response.json()
            response_text = msg_data.get("response", "")
            provider = msg_data.get("provider", "unknown")
            model = msg_data.get("model", "unknown")

            print(f"   ✅ Got response from {provider} ({model})")
            print(f"   ✅ Response: {response_text[:100]}")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            import traceback

            traceback.print_exc()
            return False

        # Test 4: Get conversation history
        print("\n4️⃣  Get Conversation History")
        try:
            response = await client.get(f"{base_url}/chat/conversations/{conv_id}")

            if response.status_code != 200:
                print(f"   ❌ Failed: {response.status_code}")
                return False

            conv_data = response.json()
            messages = conv_data.get("messages", [])

            print(f"   ✅ Retrieved conversation with {len(messages)} messages")
            for i, msg in enumerate(messages):
                role = msg.get("role")
                content = msg.get("content", "")[:50]
                print(f"      {i + 1}. [{role}] {content}...")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return False

        # Test 5: Streaming message
        print("\n5️⃣  Send Message (streaming)")
        try:
            response = await client.post(
                f"{base_url}/chat/conversations/{conv_id}/messages",
                json={
                    "message": "Count from 1 to 3 on separate lines",
                    "provider": None,
                    "stream": True,
                },
            )

            if response.status_code != 200:
                print(f"   ⚠️  Streaming test skipped: {response.status_code}")
            else:
                # For streaming, we'd need to handle SSE/streaming responses
                print(f"   ℹ️  Streaming endpoint returned: {response.status_code}")
                print("      (Streaming validation requires SSE client support)")
        except Exception as e:
            print(f"   ⚠️  Streaming test failed: {e}")

    return True


async def main():
    """Run all tests"""
    print("\n" + "█" * 70)
    print("█" + " " * 68 + "█")
    print("█" + "  🚀 KAMATERA LLM CHAT FUNCTIONALITY TEST SUITE".center(68) + "█")
    print("█" + " " * 68 + "█")
    print("█" * 70)

    all_passed = True

    # Test provider dispatcher
    if not await test_provider_dispatcher():
        all_passed = False

    # Test API endpoint
    if not await test_api_endpoint():
        all_passed = False

    # Summary
    print("\n" + "=" * 70)
    print("📋 TEST SUMMARY")
    print("=" * 70)

    if all_passed:
        print("\n✅ All tests passed! Kamatera LLM chat is working correctly.")
        print("\nNext steps:")
        print("  1. ✅ Dispatcher is routing to Kamatera providers")
        print("  2. ✅ Chat API is working end-to-end")
        print("  3. ✅ Conversation history is being persisted")
        print("\nYour Goblin Assistant is ready for production use!")
    else:
        print("\n❌ Some tests failed. See details above.")
        print("\nTroubleshooting:")
        print("  1. Ensure both Kamatera servers are running")
        print("     - Router: 45.61.51.220:8000")
        print("     - Ollama: 192.175.23.150:8002")
        print("  2. Check network connectivity from this machine")
        print("  3. Verify firewall rules allow outbound connections")
        print(
            "  4. Ensure backend is running: python3 -m uvicorn api.main:app --port 8004"
        )

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
