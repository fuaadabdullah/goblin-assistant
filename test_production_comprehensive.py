#!/usr/bin/env python3
"""
Comprehensive Production Simulation Test for Goblin Assistant.
Tests: Authentication, Concurrency, Caching, and Error Handling.
"""

import asyncio
import aiohttp
import time
import os
from typing import Dict, Any

# Load API key from env or .env.local
API_KEY = "cef5587890c73a5316a9a2c4ed851d97beb89fd28443885aad6e570dabd5f765"


async def test_endpoint(session, method, path, json_data=None, use_auth=True):
    base_url = "http://localhost:8004"
    headers = {}
    if use_auth:
        headers["x-api-key"] = API_KEY

    start_time = time.time()
    try:
        async with session.request(
            method, f"{base_url}{path}", json=json_data, headers=headers
        ) as resp:
            duration = time.time() - start_time
            data = await resp.json() if resp.status != 204 else {}
            return resp.status, data, duration
    except Exception as e:
        return 500, {"error": str(e)}, time.time() - start_time


async def run_production_tests():
    print("🚀 Starting Production Simulation Tests")
    print("=" * 60)

    async with aiohttp.ClientSession() as session:
        # 1. Test Unauthenticated Access (Should Fail)
        print("🔐 Test 1: Unauthenticated access to /chat/conversations")
        status, data, _ = await test_endpoint(
            session,
            "POST",
            "/chat/conversations",
            {"title": "Auth Test"},
            use_auth=False,
        )
        if status == 401:
            print("✅ Successfully blocked unauthenticated request (401)")
        else:
            print(f"❌ Failed to block unauthenticated request (Status: {status})")

        # 2. Test Authenticated Access (Should Succeed)
        print("\n🔑 Test 2: Authenticated access")
        status, data, _ = await test_endpoint(
            session, "POST", "/chat/conversations", {"title": "Production Test"}
        )
        if status == 200:
            conv_id = data["conversation_id"]
            print(f"✅ Authenticated successfully. Conv ID: {conv_id}")
        else:
            print(f"❌ Authentication failed (Status: {status}): {data}")
            return

        # 3. Test Provider Execution (Kamatera)
        print("\n⚡ Test 3: Provider execution (Kamatera via Dispatcher)")
        status, data, duration = await test_endpoint(
            session,
            "POST",
            f"/chat/conversations/{conv_id}/messages",
            {"message": "What is the best way to deploy a FastAPI app?"},
        )
        if status == 200:
            print(
                f"✅ Response received in {duration:.2f}s from {data.get('provider')}"
            )
            print(f"   Model: {data.get('model')}")
        else:
            print(f"❌ Provider execution failed: {data}")

        # 4. Test Caching (Second identical request)
        # Note: Backend would need caching logic enabled for this to show difference
        print("\n💾 Test 4: Caching behavior (Repeating identical message)")
        status, data, duration2 = await test_endpoint(
            session,
            "POST",
            f"/chat/conversations/{conv_id}/messages",
            {"message": "What is the best way to deploy a FastAPI app?"},
        )
        if status == 200:
            print(f"✅ Second response received in {duration2:.2f}s")
            if duration2 < duration * 0.5:
                print("🚀 Cache Hit suspected (Significant speedup!)")
            else:
                print(
                    "ℹ️  No significant speedup observed (may be provider-side caching or no caching yet)"
                )

        # 5. Test Concurrency
        print("\n🔥 Test 5: Concurrency (3 simultaneous requests)")
        tasks = [
            test_endpoint(
                session,
                "POST",
                f"/chat/conversations/{conv_id}/messages",
                {"message": f"Question {i}"},
            )
            for i in range(3)
        ]
        results = await asyncio.gather(*tasks)
        for i, (status, data, duration) in enumerate(results):
            if status == 200:
                print(f"✅ Parallel Request {i} done in {duration:.2f}s")
            else:
                print(f"❌ Parallel Request {i} failed: {status}")

    print("\n" + "=" * 60)
    print("🎉 Production simulation tests completed!")


if __name__ == "__main__":
    asyncio.run(run_production_tests())
