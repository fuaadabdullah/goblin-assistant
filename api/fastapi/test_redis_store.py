#!/usr/bin/env python3
"""
Test script for Redis polling store integration
"""

import asyncio
import sys
import os
import pytest

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from redis_polling_store import RedisPollingStore


@pytest.mark.asyncio
async def test_redis_polling_store():
    """Test the Redis polling store functionality"""
    print("Testing Redis polling store...")

    # Initialize store
    store = RedisPollingStore()

    # Check if Redis is available
    try:
        redis_client = await store.get_redis()
        redis_client.ping()
        print("✅ Redis is available")
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")

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
        success1 = await store.add_chunk(
            stream_id, {"content": "Hello", "type": "text"}
        )
        success2 = await store.add_chunk(
            stream_id, {"content": " World", "type": "text"}
        )
        if not success1 or not success2:
            raise Exception("Failed to add chunks")
        print("   Added chunks")

        # Test polling
        print("3. Polling for chunks...")
        result = await store.poll_stream(stream_id)
        if result is None or "error" in result:
            raise Exception(f"Failed to poll stream: {result}")
        print(f"   Polled result: {len(result['chunks'])} chunks")
        last_sequence = result["last_sequence"]

        # Test polling again (should be empty since no new chunks)
        print("4. Polling again...")
        result2 = await store.poll_stream(stream_id, last_sequence)
        if result2 is None or "error" in result2:
            raise Exception(f"Failed to poll stream again: {result2}")
        print(f"   Second poll result: {len(result2['chunks'])} chunks")

        # Add another chunk
        print("5. Adding another chunk...")
        success3 = await store.add_chunk(stream_id, {"content": "!", "type": "text"})
        if not success3:
            raise Exception("Failed to add another chunk")

        # Poll for new chunk
        print("6. Polling for new chunk...")
        result3 = await store.poll_stream(stream_id, last_sequence)
        if result3 is None or "error" in result3:
            raise Exception(f"Failed to poll for new chunk: {result3}")
        print(f"   Third poll result: {len(result3['chunks'])} chunks")

        # Test completing stream
        print("7. Completing stream...")
        success4 = await store.complete_stream(stream_id)
        if not success4:
            raise Exception("Failed to complete stream")
        print("   Stream completed")

        # Test polling completed stream
        print("8. Polling completed stream...")
        result4 = await store.poll_stream(stream_id, result3["last_sequence"])
        if result4 is None or "error" in result4:
            raise Exception(f"Failed to poll completed stream: {result4}")
        print(f"   Final poll result: is_complete={result4['is_complete']}")

        print("✅ All tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        pytest.fail(f"Test failed: {e}")
