#!/usr/bin/env python3
"""
Concurrency test script for Goblin Assistant.
Simulates multiple users interacting with the AI at the same time.
"""

import asyncio
import aiohttp
import time
import random


async def send_random_message(session, base_url, user_id, conversation_id):
    """Send a random message and measure response time."""
    prompts = [
        "Explain quantum computing in one sentence.",
        "What is the capital of France?",
        "Write a 3-line poem about robots.",
        "Give me a funny fact about space.",
        "What is 123 * 456?",
        "Tell me a joke about developers.",
    ]

    prompt = random.choice(prompts)
    start_time = time.time()

    try:
        async with session.post(
            f"{base_url}/chat/conversations/{conversation_id}/messages",
            json={"message": prompt, "provider": None, "model": None},
            timeout=30,
        ) as response:
            duration = time.time() - start_time
            if response.status == 200:
                data = await response.json()
                provider = data.get("provider", "unknown")
                print(
                    f"✅ User {user_id} got response in {duration:.2f}s from {provider}"
                )
                return True, duration
            else:
                print(f"❌ User {user_id} failed with status {response.status}")
                return False, duration
    except Exception as e:
        duration = time.time() - start_time
        print(f"💥 User {user_id} encountered error after {duration:.2f}s: {e}")
        return False, duration


async def run_concurrency_test():
    """Run multiple concurrent chat sessions."""
    base_url = "http://localhost:8004"
    num_concurrent_users = 5

    async with aiohttp.ClientSession() as session:
        print(f"🚀 Starting Concurrency Test with {num_concurrent_users} users")
        print(f"📍 Target: {base_url}")
        print("=" * 60)

        # Step 1: Create a conversation for each user
        users = []
        for i in range(num_concurrent_users):
            async with session.post(
                f"{base_url}/chat/conversations",
                json={"title": f"Concurrency User {i}"},
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    users.append({"id": i, "conv_id": data["conversation_id"]})

        print(f"📝 Created {len(users)} conversations. Starting messaging...")

        # Step 2: Send messages concurrently
        tasks = [
            send_random_message(session, base_url, user["id"], user["conv_id"])
            for user in users
        ]
        results = await asyncio.gather(*tasks)

        # Summary
        successes = [r for r in results if r[0]]
        durations = [r[1] for r in results]

        print("\n" + "=" * 60)
        print("📊 CONCURRENCY TEST SUMMARY")
        print(f"Total Requests: {len(results)}")
        print(f"Successes:      {len(successes)}")
        print(f"Failures:       {len(results) - len(successes)}")
        if durations:
            print(f"Avg Duration:   {sum(durations) / len(durations):.2f}s")
            print(f"Min Duration:   {min(durations):.2f}s")
            print(f"Max Duration:   {max(durations):.2f}s")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_concurrency_test())
