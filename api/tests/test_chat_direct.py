#!/usr/bin/env python3
"""
Direct test of chat functionality to bypass dispatcher issues
"""

import os
import sys
import asyncio
import aiohttp
import json

# Test with OpenAI directly
async def test_chat_direct():
    """Test chat functionality directly with OpenAI"""
    
    # Get API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found")
        return False
    
    print("✅ OpenAI API key found")
    
    # Test direct OpenAI API call
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": "Hello! Can you briefly explain what AI models are available?"}
        ],
        "max_tokens": 100
    }
    
    print("🧪 Testing OpenAI API...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=data, timeout=30) as response:
                if response.status == 200:
                    result = await response.json()
                    message = result['choices'][0]['message']['content']
                    print("✅ OpenAI API Working!")
                    print(f"Response: {message}")
                    return True
                else:
                    print(f"❌ OpenAI API failed: {response.status}")
                    text = await response.text()
                    print(f"Error: {text}")
                    return False
        except Exception as e:
            print(f"❌ OpenAI API error: {e}")
            return False

# Test the chat endpoint with direct provider selection
async def test_chat_endpoint():
    """Test our chat endpoint with explicit provider"""
    
    print("\n🧪 Testing Chat Endpoint...")
    
    # Create conversation
    async with aiohttp.ClientSession() as session:
        try:
            # Create conversation
            async with session.post(
                "http://localhost:8000/chat/conversations",
                json={"title": "Test Direct Provider"}
            ) as response:
                if response.status == 200:
                    conv_data = await response.json()
                    conv_id = conv_data['conversation_id']
                    print(f"✅ Conversation created: {conv_id}")
                    
                    # Send message with explicit provider
                    async with session.post(
                        f"http://localhost:8000/chat/conversations/{conv_id}/messages",
                        json={
                            "message": "Hello! Can you explain the current status?",
                            "provider": "openai",
                            "model": "gpt-3.5-turbo"
                        }
                    ) as msg_response:
                        if msg_response.status == 200:
                            msg_data = await msg_response.json()
                            print(f"✅ Message sent successfully!")
                            print(f"Response: {msg_data.get('response', 'No response')}")
                            print(f"Provider: {msg_data.get('provider', 'Unknown')}")
                            return True
                        else:
                            text = await msg_response.text()
                            print(f"❌ Message failed: {msg_response.status}")
                            print(f"Error: {text}")
                            return False
                else:
                    text = await response.text()
                    print(f"❌ Conversation creation failed: {response.status}")
                    print(f"Error: {text}")
                    return False
        except Exception as e:
            print(f"❌ Chat endpoint error: {e}")
            return False

if __name__ == "__main__":
    async def main():
        print("🚀 Testing Goblin Assistant Chat Functionality")
        print("=" * 50)
        
        # Test 1: Direct OpenAI API
        openai_works = await test_chat_direct()
        
        # Test 2: Chat endpoint
        if openai_works:
            chat_works = await test_chat_endpoint()
            
            if chat_works:
                print("\n🎉 SUCCESS: Chat functionality is working!")
            else:
                print("\n❌ Chat endpoint needs fixing")
        else:
            print("\n❌ OpenAI API not working - check API key")
    
    asyncio.run(main())