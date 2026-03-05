"""
Sandbox worker for secure code execution
Processes jobs from Redis queue and executes them in hardened containers
"""

import os
import subprocess
import json
import time
import shutil
from datetime import datetime

import redis
from docker import DockerClient
from docker.errors import DockerException, APIError, ContainerError

# Configuration from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "ghcr.io/yourorg/sandbox:latest")
COSIGN_PUBLIC_KEY_PATH = os.getenv("COSIGN_PUBLIC_KEY_PATH")
MAX_JOB_MEMORY = os.getenv("MAX_JOB_MEMORY", "256m")
MAX_JOB_CPUS = float(os.getenv("MAX_JOB_CPUS", "0.25"))
JOB_TIMEOUT_SECONDS = int(os.getenv("JOB_TIMEOUT_SECONDS", "10"))
S3_BUCKET = os.getenv("S3_BUCKET")

# Initialize clients
docker_client = DockerClient(base_url="unix://var/run/docker.sock")
redis_client = redis.from_url(REDIS_URL)

def verify_image_signature(image: str) -> bool:
    """
    Verify container image signature using cosign
    Returns True if signature is valid or verification is disabled
    """
    if not COSIGN_PUBLIC_KEY_PATH:
        print(f"⚠️  Cosign public key not configured, skipping image verification for {image}")
        return True

    try:
        cmd = ["cosign", "verify", "--key", COSIGN_PUBLIC_KEY_PATH, image]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print(f"✅ Image signature verified for {image}")
            return True
        else:
            print(f"❌ Image signature verification failed for {image}: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print(f"❌ Image signature verification timed out for {image}")
        return False
    except FileNotFoundError:
        print(f"❌ Cosign not found, skipping image verification for {image}")
        return True
    except Exception as e:
        print(f"❌ Error during image verification for {image}: {str(e)}")
        return False

# Import services
from api.artifact_service import artifact_service
from api.sandbox_metrics import (
    record_job_started, record_job_completed, record_job_failed,
    record_container_killed, record_artifact_upload, record_cleanup_run
)

def upload_artifacts_to_s3(job_path: str, job_id: str) -> bool:
    """
    Upload job artifacts to S3-compatible storage using artifact service
    Returns True if successful
    """
    if not artifact_service.is_available():
        print("⚠️  Artifact storage not available, keeping artifacts local")
        return False

    try:
        uploaded_count = 0
        total_size = 0

        # Upload each artifact file
        for filename in os.listdir(job_path):
            if filename in ["stdout.log", "stderr.log"]:
                continue  # Skip log files

            filepath = os.path.join(job_path, filename)
            if os.path.isfile(filepath):
                # Upload artifact using service
                result = artifact_service.upload_artifact(job_id, filepath, filename)
                if result:
                    uploaded_count += 1
                    total_size += result.get("size_bytes", 0)

        if uploaded_count > 0:
            print(f"📤 Uploaded {uploaded_count} artifacts ({total_size} bytes) for job {job_id}")

            # Clean up local artifacts after successful upload
            for filename in os.listdir(job_path):
                if filename not in ["stdout.log", "stderr.log"]:
                    filepath = os.path.join(job_path, filename)
                    try:
                        os.remove(filepath)
                        print(f"🧹 Cleaned up local artifact: {filename}")
                    except OSError as e:
                        print(f"⚠️  Failed to remove local artifact {filename}: {e}")

            return True
        else:
            print("ℹ️  No artifacts to upload")
            return True

    except Exception as e:
        print(f"❌ Failed to upload artifacts: {str(e)}")
        return False

def run_job(job_id: str, language: str, timeout: int, runtime_args: str, job_path: str):
    """
    Execute a sandbox job in a container
    This function is called by RQ worker
    """
    job_key = f"sandbox:job:{job_id}"

    try:
        # Update job status to running
        redis_client.hset(job_key, "status", "running")
        redis_client.hset(job_key, "started_at", datetime.utcnow().isoformat())

        # Record job started metrics
        record_job_started(job_id)

        print(f"🚀 Starting sandbox job {job_id} (language: {language}, timeout: {timeout}s)")

        # Verify image signature before use
        if not verify_image_signature(SANDBOX_IMAGE):
            error_msg = "Container image signature verification failed"
            redis_client.hset(job_key, mapping={
                "status": "failed",
                "error": error_msg,
                "finished_at": datetime.utcnow().isoformat()
            })
            return

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

        # Add seccomp profile if available
        seccomp_profile = "/etc/sandbox/seccomp.json"
        if os.path.exists(seccomp_profile):
            container_config["security_opt"].append(f"seccomp={seccomp_profile}")

        # Add AppArmor profile if available
        apparmor_profile = "sandbox-runner"
        try:
            # Check if AppArmor is available and profile exists
            result = subprocess.run(
                ["apparmor_status", "--profiled"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if apparmor_profile in result.stdout:
                container_config["security_opt"].append(f"apparmor={apparmor_profile}")
        except (subprocess.SubprocessError, FileNotFoundError):
            pass  # AppArmor not available

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

            # Record job completion metrics
            record_job_completed(job_id, exit_code)

            # Upload artifacts if job succeeded
            if exit_code == 0:
                upload_success = upload_artifacts_to_s3(job_path, job_id)
                record_artifact_upload(upload_success, 0)  # Size tracked in upload function

        except subprocess.TimeoutExpired:
            print(f"⏰ Container timed out after {timeout}s, killing...")
            container.kill()
            redis_client.hset(job_key, mapping={
                "status": "failed",
                "error": f"Job timed out after {timeout} seconds",
                "finished_at": datetime.utcnow().isoformat()
            })

            # Record timeout metrics
            record_container_killed("timeout")
            record_job_failed(job_id, "timeout")

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

        # Record failure metrics
        record_job_failed(job_id, "container_error")

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"❌ {error_msg}")
        redis_client.hset(job_key, mapping={
            "status": "failed",
            "error": error_msg,
            "finished_at": datetime.utcnow().isoformat()
        })

        # Record failure metrics
        record_job_failed(job_id, "unexpected_error")

    # Clean up job directory after retention period (optional)
    # For now, keep jobs for debugging - in production, implement cleanup

if __name__ == "__main__":
    # For testing the worker directly
    print("🧪 Testing sandbox worker...")

    # Create a test job
    import uuid
    test_job_id = str(uuid.uuid4())
    test_job_path = f"/tmp/test_job_{test_job_id}"

    os.makedirs(test_job_path, exist_ok=True)

    # Write test Python code
    with open(os.path.join(test_job_path, "main.py"), "w") as f:
        f.write('print("Hello from sandbox!")\n')

    print(f"Created test job {test_job_id} in {test_job_path}")
    print("To test, run: rq worker sandbox-jobs")
    print("Then submit a job via the API")