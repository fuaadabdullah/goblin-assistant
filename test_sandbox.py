#!/usr/bin/env python
"""
Simple test script to verify sandbox execution works without RQ
"""
import os
import subprocess
import tempfile
import shutil
import docker
from docker.errors import DockerException

def test_sandbox_execution():
    print("🧪 Testing sandbox execution functionality...")

    # Create test job directory
    test_job_path = "/tmp/test_sandbox_job"
    os.makedirs(test_job_path, exist_ok=True)

    # Write test Python code
    with open(os.path.join(test_job_path, "main.py"), "w") as f:
        f.write('print("Hello from sandbox!")\nprint("This is a test execution.")\n')

    # Write test JavaScript code
    with open(os.path.join(test_job_path, "main.js"), "w") as f:
        f.write('console.log("Hello from JavaScript sandbox!");')

    # Write test shell script
    with open(os.path.join(test_job_path, "script.sh"), "w") as f:
        f.write('#!/bin/bash\necho "Hello from shell script!"')

    print(f"✅ Created test files in {test_job_path}")

    # Test Python execution
    try:
        client = docker.from_env()

        # Container configuration
        binds = {test_job_path: {"bind": "/work", "mode": "rw"}}
        container_config = {
            "image": "goblin-assistant-sandbox:latest",
            "detach": False,
            "stdin_open": False,
            "tty": False,
            "network_disabled": True,
            "mem_limit": "256m",
            "cpu_quota": int(0.25 * 100000),
            "cap_drop": ["ALL"],
            "security_opt": ["no-new-privileges"],
            "volumes": binds,
            "user": "runner",
            "read_only": True,
            "tmpfs": {"/tmp": "rw,size=64m,mode=1777"},
            "environment": {
                "SANDBOX_LANGUAGE": "python",
                "SANDBOX_TIMEOUT": "10",
                "SANDBOX_RUNTIME_ARGS": ""
            }
        }

        print("🐳 Starting Python test container...")
        container = client.containers.run(**container_config)

        # When detach=False, run() returns the output directly
        # We need to run it with detach=True to get container object
        container_config["detach"] = True
        container = client.containers.run(**container_config)

        # Wait for completion
        result = container.wait(timeout=30)
        exit_code = result.get("StatusCode", -1)

        # Get logs
        logs = container.logs(stdout=True, stderr=True).decode('utf-8', errors='replace')
        print(f"📝 Container exit code: {exit_code}")
        print(f"📝 Container logs:\n{logs}")

        # Clean up
        container.remove(force=True)

        if exit_code == 0 and "Hello from sandbox!" in logs:
            print("✅ Python sandbox execution successful!")
            return True
        else:
            print("❌ Python sandbox execution failed!")
            return False

    except DockerException as e:
        print(f"❌ Docker error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    finally:
        # Clean up test files
        shutil.rmtree(test_job_path, ignore_errors=True)

if __name__ == "__main__":
    success = test_sandbox_execution()
    exit(0 if success else 1)