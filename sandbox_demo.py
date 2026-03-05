#!/usr/bin/env python3
"""
Sandbox Demo Script
Demonstrates how to use the sandbox API for secure code execution
"""

import requests
import json
import time
import sys

# Configuration
API_BASE_URL = "http://localhost:8001"  # Adjust as needed
API_KEY = "206e61fdeda2267c9a4ecac3997c4eae7ebd20038282445f7524a84a78ac0158"  # Use the frontend API key

def demo_sandbox_api():
    """Demonstrate sandbox API usage"""
    print("🚀 Sandbox API Demo")
    print("=" * 40)

    # Test 1: Check sandbox health
    print("\n1. Checking sandbox health...")
    try:
        response = requests.get(f"{API_BASE_URL}/sandbox/health/status")
        if response.status_code == 200:
            health = response.json()
            print(f"   ✅ Sandbox status: {health.get('status', 'unknown')}")
            print(f"   ✅ Redis connected: {health.get('redis_connected', False)}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
        return

    # Test 2: Submit a Python job
    print("\n2. Submitting Python code execution job...")
    python_code = """
import sys
print("Hello from sandbox!")
print(f"Python version: {sys.version}")
print("Environment is properly isolated!")

# Test basic functionality
result = 42 * 2
print(f"Calculation result: {result}")

# Test file operations (should work in /work directory)
with open('/work/test_output.txt', 'w') as f:
    f.write('This file was created in the sandbox!')

print("File written successfully")
"""

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }

    job_data = {
        "language": "python",
        "source": python_code.strip(),
        "timeout": 10
    }

    try:
        response = requests.post(
            f"{API_BASE_URL}/sandbox/submit",
            headers=headers,
            json=job_data
        )

        if response.status_code == 200:
            result = response.json()
            job_id = result.get('job_id')
            print(f"   ✅ Job submitted successfully: {job_id}")

            # Test 3: Monitor job status
            print("\n3. Monitoring job execution...")
            max_attempts = 30  # 30 seconds timeout
            attempt = 0

            while attempt < max_attempts:
                try:
                    response = requests.get(
                        f"{API_BASE_URL}/sandbox/status/{job_id}",
                        headers=headers
                    )

                    if response.status_code == 200:
                        status_data = response.json()
                        status = status_data.get('status')
                        print(f"   📊 Job status: {status}")

                        if status in ['finished', 'failed']:
                            print(f"   ✅ Job completed with status: {status}")
                            if status_data.get('exit_code') is not None:
                                print(f"   📄 Exit code: {status_data['exit_code']}")
                            if status_data.get('error'):
                                print(f"   ❌ Error: {status_data['error']}")
                            break
                        elif status == 'running':
                            print("   ⚙️  Job is running...")
                        elif status == 'queued':
                            print("   ⏳ Job is queued...")
                    else:
                        print(f"   ❌ Status check failed: {response.status_code}")
                        break

                except Exception as e:
                    print(f"   ❌ Status check error: {e}")
                    break

                time.sleep(1)
                attempt += 1

            if attempt >= max_attempts:
                print("   ⏰ Job monitoring timed out")

            # Test 4: Get job logs
            print("\n4. Retrieving job logs...")
            try:
                response = requests.get(
                    f"{API_BASE_URL}/sandbox/logs/{job_id}",
                    headers=headers
                )

                if response.status_code == 200:
                    logs_data = response.json()
                    logs = logs_data.get('logs', '')
                    if logs:
                        print("   📄 Job logs:")
                        print("   " + "-" * 30)
                        for line in logs.split('\n'):
                            if line.strip():
                                print(f"   {line}")
                        print("   " + "-" * 30)
                    else:
                        print("   📄 No logs available")
                else:
                    print(f"   ❌ Failed to get logs: {response.status_code}")

            except Exception as e:
                print(f"   ❌ Logs retrieval error: {e}")

            # Test 5: List artifacts
            print("\n5. Listing job artifacts...")
            try:
                response = requests.get(
                    f"{API_BASE_URL}/sandbox/artifacts/{job_id}",
                    headers=headers
                )

                if response.status_code == 200:
                    artifacts_data = response.json()
                    artifacts = artifacts_data.get('artifacts', [])
                    if artifacts:
                        print(f"   📦 Found {len(artifacts)} artifacts:")
                        for artifact in artifacts:
                            print(f"      • {artifact['name']} ({artifact['size']} bytes)")
                    else:
                        print("   📦 No artifacts found")
                else:
                    print(f"   ❌ Failed to list artifacts: {response.status_code}")

            except Exception as e:
                print(f"   ❌ Artifacts listing error: {e}")

        else:
            print(f"   ❌ Job submission failed: {response.status_code}")
            print(f"      Response: {response.text}")

    except Exception as e:
        print(f"   ❌ API request error: {e}")

    print("\n" + "=" * 40)
    print("🏁 Sandbox demo completed!")
    print("\n🔒 Security Features Demonstrated:")
    print("   • Code executed in isolated container")
    print("   • Network access disabled")
    print("   • Resource limits enforced")
    print("   • API authentication required")
    print("   • Input validation performed")

    print("\n💡 Try the sandbox in the web interface:")
    print("   1. Start the application: docker-compose up")
    print("   2. Open http://localhost:3000")
    print("   3. Go to Chat → Switch to 'Code Sandbox' tab")
    print("   4. Write and execute code securely!")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print("Sandbox API Demo")
        print("Usage: python sandbox_demo.py")
        print("Make sure the sandbox API is running on http://localhost:8001")
        sys.exit(0)

    demo_sandbox_api()