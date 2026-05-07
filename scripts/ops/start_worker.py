#!/usr/bin/env python
"""
RQ worker for sandbox jobs
"""
import sys
import os
import redis
from rq import Worker, Queue

# Add current directory to Python path
sys.path.insert(0, '/home/runner')

def run_job(job_id: str, language: str, timeout: int, runtime_args: str, job_path: str):
    """
    Execute a sandbox job in a container
    This function is called by RQ worker
    """
    import subprocess
    import json
    import shutil
    from datetime import datetime
    from docker import DockerClient
    from docker.errors import DockerException

    # Configuration
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
    SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "goblin-assistant-sandbox:latest")
    MAX_JOB_MEMORY = os.getenv("MAX_JOB_MEMORY", "256m")
    MAX_JOB_CPUS = float(os.getenv("MAX_JOB_CPUS", "0.25"))
    JOB_TIMEOUT_SECONDS = int(os.getenv("JOB_TIMEOUT_SECONDS", "10"))

    # Initialize clients
    docker_client = DockerClient(base_url="unix://var/run/docker.sock")
    redis_client = redis.from_url(REDIS_URL)

    job_key = f"sandbox:job:{job_id}"

    try:
        # Update job status to running
        redis_client.hset(job_key, "status", "running")
        redis_client.hset(job_key, "started_at", datetime.utcnow().isoformat())

        print(f"🚀 Starting sandbox job {job_id} (language: {language}, timeout: {timeout}s)")

        # Determine command based on language
        if language == "python":
            command = ["python", "/work/main.py"]
            if runtime_args:
                command.extend(runtime_args.split())
        elif language == "javascript":
            command = ["node", "/work/main.js"]
            if runtime_args:
                command.extend(runtime_args.split())
        elif language == "bash":
            command = ["bash", "/work/script.sh"]
            if runtime_args:
                command.extend(runtime_args.split())
        else:
            error_msg = f"Unsupported language: {language}"
            redis_client.hset(job_key, mapping={
                "status": "failed",
                "error": error_msg,
                "finished_at": datetime.utcnow().isoformat()
            })
            return

        # Container configuration with security hardening
        binds = {job_path: {"bind": "/work", "mode": "rw"}}
        container_config = {
            "image": SANDBOX_IMAGE,
            "command": command,
            "detach": True,
            "stdin_open": False,
            "tty": False,
            "network_disabled": True,  # No network access
            "mem_limit": MAX_JOB_MEMORY,
            "cpu_quota": int(MAX_JOB_CPUS * 100000),  # Docker CPU quota
            "cap_drop": ["ALL"],  # Drop all capabilities
            "security_opt": [
                "no-new-privileges",  # Prevent privilege escalation
            ],
            "volumes": binds,
            "working_dir": "/work",
            "user": "runner",  # Non-root user
            "read_only": True,  # Read-only root filesystem
            "tmpfs": {  # Temporary writable directory
                "/tmp": "rw,size=64m,mode=1777"
            },
        }

        print(f"🐳 Creating container with config: {json.dumps(container_config, indent=2)}")

        # Create and start container
        container = docker_client.containers.run(**container_config)

        print(f"✅ Container {container.id[:12]} started for job {job_id}")

        # Wait for completion with timeout
        try:
            result = container.wait(timeout=timeout)
            exit_code = result.get("StatusCode", -1)
            print(f"✅ Container finished with exit code {exit_code}")

            # Capture logs
            logs = container.logs(stdout=True, stderr=True).decode('utf-8', errors='replace')
            log_file = os.path.join(job_path, "stdout.log")
            with open(log_file, "w") as f:
                f.write(logs)

            # Update job status
            job_update = {
                "status": "finished" if exit_code == 0 else "failed",
                "exit_code": str(exit_code),
                "finished_at": datetime.utcnow().isoformat()
            }

            if exit_code != 0:
                job_update["error"] = f"Container exited with code {exit_code}"

            redis_client.hset(job_key, mapping=job_update)

        except subprocess.TimeoutExpired:
            print(f"⏰ Container timed out after {timeout}s, killing...")
            container.kill()
            redis_client.hset(job_key, mapping={
                "status": "failed",
                "error": f"Job timed out after {timeout} seconds",
                "finished_at": datetime.utcnow().isoformat()
            })

        finally:
            # Always clean up container
            try:
                container.remove(force=True)
                print(f"🧹 Cleaned up container for job {job_id}")
            except Exception as e:
                print(f"⚠️  Failed to remove container: {str(e)}")

    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        print(f"❌ {error_msg}")
        redis_client.hset(job_key, mapping={
            "status": "failed",
            "error": error_msg,
            "finished_at": datetime.utcnow().isoformat()
        })

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"❌ {error_msg}")
        redis_client.hset(job_key, mapping={
            "status": "failed",
            "error": error_msg,
            "finished_at": datetime.utcnow().isoformat()
        })

# Start RQ worker
if __name__ == '__main__':
    # Connect to Redis
    redis_conn = redis.from_url(os.getenv('REDIS_URL', 'redis://redis:6379/0'))

    # Create queue
    queue = Queue('sandbox-jobs', connection=redis_conn)

    print("🚀 Starting RQ worker for sandbox-jobs queue...")
    worker = Worker([queue])
    worker.work()