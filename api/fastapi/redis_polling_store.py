# Redis-based polling storage for high concurrency streaming
import redis
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import os


class RedisPollingStore:
    """Redis-based storage for polling-based streaming with high concurrency support"""

    def __init__(self, redis_url: str = None, ttl_seconds: int = 3600):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.ttl_seconds = ttl_seconds
        self._redis = None

    async def get_redis(self):
        """Lazy initialization of Redis connection"""
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    async def create_stream(
        self, stream_id: str, initial_data: Dict[str, Any] = None
    ) -> bool:
        """Create a new polling stream"""
        try:
            redis_client = await self.get_redis()

            stream_data = {
                "created_at": datetime.utcnow().isoformat(),
                "status": "active",
                "chunks": [],
                "metadata": initial_data or {},
                "last_poll": None,
                "total_chunks": 0,
                "is_complete": False,
            }

            # Store stream data
            key = f"stream:{stream_id}"
            redis_client.setex(key, self.ttl_seconds, json.dumps(stream_data))

            # Add to active streams set for monitoring
            redis_client.sadd("active_streams", stream_id)
            redis_client.expire("active_streams", self.ttl_seconds)

            return True
        except Exception as e:
            print(f"Error creating stream {stream_id}: {e}")
            return False

    async def add_chunk(self, stream_id: str, chunk: Any) -> bool:
        """Add a chunk to an existing stream"""
        try:
            redis_client = await self.get_redis()
            key = f"stream:{stream_id}"

            # Get current stream data
            stream_json = redis_client.get(key)
            if not stream_json:
                return False

            stream_data = json.loads(stream_json)

            # Check if stream is still active
            if stream_data.get("status") != "active":
                return False

            # Add chunk
            chunk_data = {
                "data": chunk,
                "timestamp": datetime.utcnow().isoformat(),
                "sequence": len(stream_data["chunks"]),
            }

            stream_data["chunks"].append(chunk_data)
            stream_data["total_chunks"] = len(stream_data["chunks"])
            stream_data["last_updated"] = datetime.utcnow().isoformat()

            # Save updated stream data
            redis_client.setex(key, self.ttl_seconds, json.dumps(stream_data))

            return True
        except Exception as e:
            print(f"Error adding chunk to stream {stream_id}: {e}")
            return False

    async def poll_stream(
        self, stream_id: str, last_sequence: int = -1
    ) -> Optional[Dict[str, Any]]:
        """Poll for new chunks in a stream"""
        try:
            redis_client = await self.get_redis()
            key = f"stream:{stream_id}"

            stream_json = redis_client.get(key)
            if not stream_json:
                return {"error": "stream_not_found"}

            stream_data = json.loads(stream_json)

            # Update last poll time
            stream_data["last_poll"] = datetime.utcnow().isoformat()
            redis_client.setex(key, self.ttl_seconds, json.dumps(stream_data))

            # Get new chunks since last_sequence
            all_chunks = stream_data.get("chunks", [])
            new_chunks = []

            if last_sequence < 0:
                # Return all chunks for new pollers
                new_chunks = all_chunks
            else:
                # Return only new chunks
                for i, chunk in enumerate(all_chunks):
                    if i > last_sequence:
                        new_chunks.append(chunk)

            return {
                "stream_id": stream_id,
                "chunks": new_chunks,
                "total_chunks": len(all_chunks),
                "new_chunks_count": len(new_chunks),
                "is_complete": stream_data.get("is_complete", False),
                "status": stream_data.get("status", "unknown"),
                "last_sequence": len(all_chunks) - 1 if all_chunks else -1,
            }

        except Exception as e:
            print(f"Error polling stream {stream_id}: {e}")
            return {"error": "internal_error"}

    async def complete_stream(self, stream_id: str) -> bool:
        """Mark a stream as completed"""
        try:
            redis_client = await self.get_redis()
            key = f"stream:{stream_id}"

            stream_json = redis_client.get(key)
            if not stream_json:
                return False

            stream_data = json.loads(stream_json)
            stream_data["is_complete"] = True
            stream_data["status"] = "completed"
            stream_data["completed_at"] = datetime.utcnow().isoformat()

            redis_client.setex(key, self.ttl_seconds, json.dumps(stream_data))
            return True

        except Exception as e:
            print(f"Error completing stream {stream_id}: {e}")
            return False

    async def cancel_stream(self, stream_id: str) -> bool:
        """Cancel a stream"""
        try:
            redis_client = await self.get_redis()
            key = f"stream:{stream_id}"

            stream_json = redis_client.get(key)
            if not stream_json:
                return False

            stream_data = json.loads(stream_json)
            stream_data["is_complete"] = True
            stream_data["status"] = "cancelled"
            stream_data["cancelled_at"] = datetime.utcnow().isoformat()

            redis_client.setex(key, self.ttl_seconds, json.dumps(stream_data))

            # Remove from active streams
            redis_client.srem("active_streams", stream_id)

            return True

        except Exception as e:
            print(f"Error cancelling stream {stream_id}: {e}")
            return False

    async def get_active_streams(self) -> List[str]:
        """Get list of active stream IDs"""
        try:
            redis_client = await self.get_redis()
            return redis_client.smembers("active_streams")
        except Exception as e:
            print(f"Error getting active streams: {e}")
            return []

    async def cleanup_expired_streams(self) -> int:
        """Clean up expired streams (called by background task)"""
        try:
            redis_client = await self.get_redis()
            active_streams = redis_client.smembers("active_streams")

            cleaned_count = 0
            for stream_id in active_streams:
                key = f"stream:{stream_id}"
                if not redis_client.exists(key):
                    redis_client.srem("active_streams", stream_id)
                    cleaned_count += 1

            return cleaned_count

        except Exception as e:
            print(f"Error cleaning up expired streams: {e}")
            return 0

    async def get_stream_stats(self) -> Dict[str, Any]:
        """Get statistics about streams"""
        try:
            redis_client = await self.get_redis()
            active_count = redis_client.scard("active_streams")

            # Get memory usage info
            info = redis_client.info("memory")
            used_memory = info.get("used_memory_human", "unknown")

            return {
                "active_streams": active_count,
                "redis_memory_used": used_memory,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            print(f"Error getting stream stats: {e}")
            return {"error": "stats_unavailable"}


# Global instance for the application
polling_store = RedisPollingStore()


# Background cleanup task
async def cleanup_expired_streams_task():
    """Background task to clean up expired streams"""
    while True:
        try:
            cleaned = await polling_store.cleanup_expired_streams()
            if cleaned > 0:
                print(f"Cleaned up {cleaned} expired streams")
        except Exception as e:
            print(f"Error in cleanup task: {e}")

        await asyncio.sleep(300)  # Run every 5 minutes


# Start cleanup task
def start_cleanup_task():
    """Start the background cleanup task"""
    asyncio.create_task(cleanup_expired_streams_task())
