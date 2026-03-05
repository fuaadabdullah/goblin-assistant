#!/usr/bin/env python3
"""
Test script to verify Kamatera provider integration.
Tests connectivity and functionality of both Kamatera providers.
"""

import asyncio
import sys
import os

# Add the API directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

from api.providers.dispatcher_fixed import ProviderDispatcher
import httpx


async def test_kamatera_connectivity():
    """Test basic connectivity to Kamatera servers"""
    print("🔍 Testing Kamatera Server Connectivity")
    print("=" * 50)
    
    # Test Server 2 (Ollama)
    print("\n📡 Testing Server 2 (Ollama) - 192.175.23.150:8002")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://192.175.23.150:8002/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [model["name"] for model in data.get("models", [])]
                print(f"✅ Server 2 (Ollama) is healthy")
                print(f"   Models available: {len(models)}")
                print(f"   Sample models: {models[:5]}")
            else:
                print(f"❌ Server 2 (Ollama) returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Server 2 (Ollama) connection failed: {str(e)}")
    
    # Test Server 1 (Router)
    print("\n📡 Testing Server 1 (Router) - 45.61.51.220:8000")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://45.61.51.220:8000/health")
            if response.status_code == 200:
                print(f"✅ Server 1 (Router) is healthy")
                print(f"   Health response: {response.text[:100]}...")
            else:
                print(f"❌ Server 1 (Router) returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Server 1 (Router) connection failed: {str(e)}")


async def test_kamatera_providers():
    """Test Kamatera provider implementations"""
    print("\n\n🧪 Testing Kamatera Provider Implementations")
    print("=" * 50)
    
    dispatcher = ProviderDispatcher()
    
    # Test Ollama Kamatera Provider
    print("\n🔧 Testing Ollama Kamatera Provider")
    try:
        provider = dispatcher.get_provider("ollama_kamatera")
        print(f"✅ Provider created successfully: {type(provider).__name__}")
        
        # Test a simple chat completion
        result = await dispatcher.invoke_provider(
            provider_id="ollama_kamatera",
            model="phi3:latest",
            payload={"messages": [{"role": "user", "content": "Hello! Please respond with just 'Hello World'."}]},
            timeout_ms=30000,
            stream=False
        )
        
        if result.get("ok"):
            print(f"✅ Chat completion successful!")
            print(f"   Response: {result['result']['text'][:100]}...")
            print(f"   Latency: {result.get('latency_ms', 0):.0f}ms")
        else:
            print(f"❌ Chat completion failed: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Ollama Kamatera Provider test failed: {str(e)}")
    
    # Test llama.cpp Kamatera Provider
    print("\n🔧 Testing llama.cpp Kamatera Provider")
    try:
        provider = dispatcher.get_provider("llamacpp_kamatera")
        print(f"✅ Provider created successfully: {type(provider).__name__}")
        
        # Test a simple chat completion
        result = await dispatcher.invoke_provider(
            provider_id="llamacpp_kamatera",
            model="qwen2.5:latest",
            payload={"messages": [{"role": "user", "content": "Hello! Please respond with just 'Hello World'."}]},
            timeout_ms=30000,
            stream=False
        )
        
        if result.get("ok"):
            print(f"✅ Chat completion successful!")
            print(f"   Response: {result['result']['text'][:100]}...")
            print(f"   Latency: {result.get('latency_ms', 0):.0f}ms")
        else:
            print(f"❌ Chat completion failed: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ llama.cpp Kamatera Provider test failed: {str(e)}")


async def test_auto_selection():
    """Test auto-selection of Kamatera providers"""
    print("\n\n🎯 Testing Auto-Provider Selection")
    print("=" * 50)
    
    dispatcher = ProviderDispatcher()
    
    try:
        # Test auto-selection (should prefer Kamatera providers)
        selected_provider = await dispatcher._auto_select_provider()
        print(f"✅ Auto-selected provider: {selected_provider}")
        
        if "kamatera" in selected_provider:
            print("🎉 Auto-selection correctly chose a Kamatera provider!")
        else:
            print(f"ℹ️  Auto-selected non-Kamatera provider: {selected_provider}")
            print("   This is OK if Kamatera servers are unavailable")
            
    except Exception as e:
        print(f"❌ Auto-selection failed: {str(e)}")


async def main():
    """Run all tests"""
    print("🚀 Kamatera Integration Test Suite")
    print("=" * 60)
    print("This script tests the complete Kamatera provider integration")
    print()
    
    # Run tests
    await test_kamatera_connectivity()
    await test_kamatera_providers()
    await test_auto_selection()
    
    print("\n\n📋 Test Summary")
    print("=" * 60)
    print("If you see ✅ symbols above, the Kamatera integration is working!")
    print("If you see ❌ symbols, check the server connectivity and configuration.")
    print()
    print("Next steps:")
    print("1. Ensure both Kamatera servers are running")
    print("2. Check firewall settings allow connections from the backend")
    print("3. Verify the models are available on the servers")
    print("4. Test through the main chat API endpoints")


if __name__ == "__main__":
    asyncio.run(main())