#!/usr/bin/env python3
"""
Development sandbox worker - runs code directly without Docker containers
For testing purposes only - not secure for production
"""

import os
import sys
import subprocess
import time
import json
from typing import Dict, Any
import redis
from rq import Worker, Queue

def run_job_dev(job_id: str, language: str, timeout: int, runtime_args: str, job_path: str):
    """
    Run a sandbox job directly (development mode - not secure)
    """
    job_key = f"sandbox:job:{job_id}"
    r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

    try:
        # Update job status to running
        r.hset(job_key, "status", "running")
        r.hset(job_key, "started_at", time.time())

        print(f"🧪 Running job {job_id} directly (dev mode) - language: {language}")

        # Determine command based on language
        if language == "python":
            command = ["python", os.path.join(job_path, "main.py")]
            if runtime_args:
                command.extend(runtime_args.split())
        elif language == "javascript":
            command = ["node", os.path.join(job_path, "main.js")]
            if runtime_args:
                command.extend(runtime_args.split())
        elif language == "bash":
            command = ["bash", os.path.join(job_path, "script.sh")]
            if runtime_args:
                command.extend(runtime_args.split())
        else:
            error_msg = f"Unsupported language: {language}"
            r.hset(job_key, mapping={
                "status": "failed",
                "error": error_msg,
                "finished_at": time.time()
            })
            return

        print(f"Executing: {' '.join(command)}")

        # Run the command with timeout
        try:
            result = subprocess.run(
                command,
                cwd=job_path,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            # Write output to log file
            log_file = os.path.join(job_path, "stdout.log")
            with open(log_file, "w") as f:
                f.write(result.stdout)
                if result.stderr:
                    f.write("\n--- STDERR ---\n")
                    f.write(result.stderr)

            # Update job status
            job_update = {
                "status": "finished" if result.returncode == 0 else "failed",
                "exit_code": str(result.returncode),
                "finished_at": time.time()
            }

            if result.returncode != 0:
                job_update["error"] = f"Process exited with code {result.returncode}"

            r.hset(job_key, mapping=job_update)

            print(f"✅ Job {job_id} completed with exit code {result.returncode}")

        except subprocess.TimeoutExpired:
            error_msg = f"Job timed out after {timeout} seconds"
            r.hset(job_key, mapping={
                "status": "failed",
                "error": error_msg,
                "finished_at": time.time()
            })
            print(f"⏰ Job {job_id} timed out")

        except Exception as e:
            error_msg = f"Execution error: {str(e)}"
            r.hset(job_key, mapping={
                "status": "failed",
                "error": error_msg,
                "finished_at": time.time()
            })
            print(f"❌ Job {job_id} failed: {error_msg}")

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"💥 Critical error in job {job_id}: {error_msg}")
        try:
            r.hset(job_key, mapping={
                "status": "failed",
                "error": error_msg,
                "finished_at": time.time()
            })
        except:
            pass

# Alias for compatibility with production API
run_job = run_job_dev

if __name__ == '__main__':
    print("🧪 Starting development sandbox worker (direct execution - not secure)")
    print("⚠️  WARNING: This runs code directly without container isolation!")
    print("   Only use for development testing.")

    # Use dev version for local testing
    import sandbox_worker_dev
    sys.modules['sandbox_worker'] = sandbox_worker_dev

    # Start RQ worker
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_conn = redis.from_url(redis_url)
    queue = Queue("sandbox-jobs", connection=redis_conn)

    worker = Worker([queue], name='sandbox-worker-dev', connection=redis_conn)
    worker.work()