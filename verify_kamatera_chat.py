#!/usr/bin/env python3
"""
Quick verification script for Kamatera LLM chat functionality.
Run this to confirm the system is working.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "api"))

from api.providers.dispatcher_fixed import ProviderDispatcher


async def quick_verify():
    """Quick verification that Kamatera LLM chat is working"""
    print("\n🚀 Kamatera LLM Chat - Quick Verification\n")

    dispatcher = ProviderDispatcher()

    # Test 1: Can we reach the provider?
    print("1. Checking provider availability...")
    try:
        dispatcher.get_provider("llamacpp_kamatera")
        print("   ✅ Provider loaded\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        return False

    # Test 2: Get a response
    print("2. Testing chat completion...")
    try:
        result = await dispatcher.invoke_provider(
            provider_id="llamacpp_kamatera",
            model="qwen2.5:latest",
            payload={
                "messages": [
                    {"role": "user", "content": "Say 'Kamatera LLM is working!'"}
                ]
            },
            timeout_ms=30000,
            stream=False,
        )

        if result.get("ok"):
            response = result.get("result", {}).get("text", "")
            print(f"   ✅ Got response: '{response.strip()}'\n")
        else:
            error = result.get("error", "unknown")
            print(f"   ❌ Error: {error}\n")
            return False
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        return False

    # Test 3: Verify format
    print("3. Verifying response format...")
    required_keys = ["ok", "result", "latency_ms"]
    missing = [k for k in required_keys if k not in result]

    if not missing:
        print("   ✅ Response format valid\n")
    else:
        print(f"   ❌ Missing keys: {missing}\n")
        return False

    # Success!
    print("=" * 50)
    print("✅ KAMATERA LLM CHAT IS WORKING!")
    print("=" * 50)
    print("\nYour Goblin Assistant is ready to chat using:")
    print("  • Server: 45.61.51.220:8000")
    print("  • Model: qwen2.5:latest")
    print(f"  • Latency: {result.get('latency_ms', 0):.0f}ms")
    print("\nYou can now:")
    print("  1. Create conversations via /chat/conversations")
    print("  2. Send messages via /chat/conversations/{id}/messages")
    print("  3. Get full chat history via /chat/conversations/{id}")
    print()

    return True


if __name__ == "__main__":
    success = asyncio.run(quick_verify())
    sys.exit(0 if success else 1)
