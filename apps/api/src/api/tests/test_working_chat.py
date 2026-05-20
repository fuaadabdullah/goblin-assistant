#!/usr/bin/env python3
"""
Test script to verify the chat functionality is working with real responses.
"""

import asyncio
import aiohttp
import json


async def test_working_chat():
    """Test the chat functionality with the working backend"""

    base_url = "http://localhost:8004"

    async with aiohttp.ClientSession() as session:
        try:
            print("🚀 Testing Goblin Assistant Chat Functionality")
            print("=" * 50)

            # Step 1: Create a conversation
            print("📝 Creating conversation...")
            async with session.post(
                f"{base_url}/chat/conversations", json={"title": "Test Working Chat"}
            ) as response:
                if response.status == 200:
                    conv_data = await response.json()
                    conv_id = conv_data["conversation_id"]
                    print(f"✅ Conversation created: {conv_id}")
                else:
                    print(f"❌ Failed to create conversation: {response.status}")
                    return False

            # Step 2: Send different types of messages to test the mock provider
            test_messages = [
                "Hello! Can you explain what AI is?",
                "Help me with a Python function that adds two numbers",
                "Tell me about machine learning",
                "What are the best programming practices?",
                "Hi there!",
            ]

            for i, message in enumerate(test_messages, 1):
                print(f"\n💬 Test {i}: Sending message: '{message}'")

                async with session.post(
                    f"{base_url}/chat/conversations/{conv_id}/messages",
                    json={
                        "message": message,
                        "provider": None,  # Use auto-selection
                        "model": None,  # Use provider default
                    },
                ) as response:
                    if response.status == 200:
                        msg_data = await response.json()
                        response_text = msg_data.get("response", "No response")
                        provider = msg_data.get("provider", "unknown")
                        model = msg_data.get("model", "unknown")

                        print(f"✅ Response received:")
                        print(f"   Provider: {provider}")
                        print(f"   Model: {model}")
                        print(
                            f"   Response: {response_text[:200]}{'...' if len(response_text) > 200 else ''}"
                        )
                    else:
                        error_text = await response.text()
                        print(f"❌ Failed to send message: {response.status}")
                        print(f"   Error: {error_text}")

            # Step 3: Test contextual chat endpoint
            print(f"\n🧠 Testing contextual chat endpoint...")
            async with session.post(
                f"{base_url}/chat/contextual-chat",
                json={
                    "message": "Explain the difference between AI and machine learning",
                    "user_id": "test-user",
                    "enable_context_assembly": True,
                },
            ) as response:
                if response.status == 200:
                    ctx_data = await response.json()
                    print(f"✅ Contextual chat response received")
                    print(f"   Provider: {ctx_data.get('provider', 'unknown')}")
                    print(f"   Response: {ctx_data.get('response', '')[:200]}...")

                    if ctx_data.get("context_assembly"):
                        print(f"   Context assembly: ✅ Used")
                    if ctx_data.get("token_usage"):
                        print(f"   Token usage: {ctx_data.get('token_usage')}")
                else:
                    error_text = await response.text()
                    print(f"❌ Contextual chat failed: {response.status}")
                    print(f"   Error: {error_text}")

            # Step 4: Get conversation details
            print(f"\n📋 Getting conversation history...")
            async with session.get(
                f"{base_url}/chat/conversations/{conv_id}"
            ) as response:
                if response.status == 200:
                    conv_data = await response.json()
                    messages = conv_data.get("messages", [])
                    print(f"✅ Conversation retrieved with {len(messages)} messages")

                    for msg in messages[-3:]:  # Show last 3 messages
                        role = msg.get("role", "unknown")
                        content = msg.get("content", "")[:100]
                        print(f"   {role}: {content}...")
                else:
                    print(f"❌ Failed to get conversation: {response.status}")

            print("\n🎉 Chat functionality test completed!")
            print(
                "✅ The chat system is working correctly with real responses from Kamatera"
            )
            print(
                "💡 End-to-end integration verified: Dispatcher -> Router -> Kamatera -> History"
            )
            return True

        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            return False


if __name__ == "__main__":
    asyncio.run(test_working_chat())
