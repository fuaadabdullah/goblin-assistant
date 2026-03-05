#!/usr/bin/env python3
"""
Start RQ worker for sandbox jobs
"""

import os
import sys
from rq import Worker, Queue
from redis import Redis

# Add current directory to path so we can import sandbox_worker
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the job function
from sandbox_worker import run_job

# Configure Redis connection
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_conn = Redis.from_url(redis_url)

# Create queue
queue = Queue("sandbox-jobs", connection=redis_conn)

# Start worker
if __name__ == '__main__':
    worker = Worker([queue], name='sandbox-worker-production', connection=redis_conn)
    worker.work()