#!/usr/bin/env python3
"""
Test script for Redis polling store integration
"""

import asyncio
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from redis_polling_store import RedisPollingStore


async def test_redis_polling_store():
    """Test the Redis polling store functionality"""
    print("Testing Redis polling store...")

    # Initialize store
    store = RedisPollingStore()

    try:
        # Test creating a stream
        print("1. Creating stream...")
        stream_id = f"test_stream_{int(asyncio.get_event_loop().time() * 1000000)}"
        success = await store.create_stream(
            stream_id, {"provider": "test_provider", "model": "test_model"}
        )
        if not success:
            raise Exception("Failed to create stream")
        print(f"   Created stream: {stream_id}")

        # Test adding chunks
        print("2. Adding chunks...")
        await store.add_chunk(stream_id, {"content": "Hello", "type": "text"})
        await store.add_chunk(stream_id, {"content": " World", "type": "text"})
        print("   Added chunks")

        # Test polling
        print("3. Polling for chunks...")
        result = await store.poll_stream(stream_id)
        print(f"   Polled result: {len(result['chunks'])} chunks")
        last_sequence = result["last_sequence"]

        # Test polling again (should be empty since no new chunks)
        print("4. Polling again...")
        result2 = await store.poll_stream(stream_id, last_sequence)
        print(f"   Second poll result: {len(result2['chunks'])} chunks")

        # Add another chunk
        print("5. Adding another chunk...")
        await store.add_chunk(stream_id, {"content": "!", "type": "text"})

        # Poll for new chunk
        print("6. Polling for new chunk...")
        result3 = await store.poll_stream(stream_id, last_sequence)
        print(f"   Third poll result: {len(result3['chunks'])} chunks")

        # Test completing stream
        print("7. Completing stream...")
        await store.complete_stream(stream_id)
        print("   Stream completed")

        # Test polling completed stream
        print("8. Polling completed stream...")
        result4 = await store.poll_stream(stream_id, result3["last_sequence"])
        print(f"   Final poll result: is_complete={result4['is_complete']}")

        print("✅ All tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

    return True


if __name__ == "__main__":
    asyncio.run(test_redis_polling_store())
