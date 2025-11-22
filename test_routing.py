#!/usr/bin/env python3
"""
Test script for the intelligent routing system integration.
This demonstrates how the goblin assistant now uses intelligent provider routing.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).resolve().parent / "src"))

from routing.router import route_task_sync, top_providers_for


def test_routing():
    """Test the intelligent routing system"""

    print("🧠 Goblin Assistant - Intelligent Routing System Test")
    print("=" * 60)

    # Test 1: Show top providers for different capabilities
    print("\n📊 Top Providers by Capability:")
    capabilities = ["chat", "reasoning", "code", "embedding", "image"]
    for cap in capabilities:
        top_providers = top_providers_for(cap, limit=3)
        print(f"  {cap.capitalize()}: {', '.join(top_providers)}")

    # Test 2: Route a reasoning task
    print("\n🧪 Routing Test - Reasoning Task:")
    payload = {
        "prompt": "Plan a 3-step refactor for a FastAPI application to reduce latency.",
        "max_tokens": 300,
    }

    try:
        result = route_task_sync("reasoning", payload, prefer_local=False)
        if result.get("ok"):
            print("  ✅ Routing successful!")
            print(f"  📍 Provider: {result['provider']}")
            print(f"  🤖 Model: {result['model']}")
            print(f"  ⏱️  Latency: {result.get('latency_ms', 0):.2f}ms")
            print(f"  📝 Result: {result['result'].get('text', 'N/A')[:100]}...")
        else:
            print(f"  ❌ Routing failed: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"  ❌ Exception: {e}")

    # Test 3: Route with cost preference
    print("\n💰 Cost-Preferred Routing Test:")
    try:
        result = route_task_sync("chat", payload, prefer_cost=True)
        if result.get("ok"):
            print("  ✅ Cost-optimized routing successful!")
            print(f"  📍 Provider: {result['provider']}")
            print(f"  🤖 Model: {result['model']}")
        else:
            print(f"  ❌ Routing failed: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"  ❌ Exception: {e}")

    print("\n🎉 Intelligent routing system integration complete!")
    print("The goblin assistant now automatically selects the best AI provider")
    print("based on capability, cost, latency, and reliability metrics.")


if __name__ == "__main__":
    test_routing()
