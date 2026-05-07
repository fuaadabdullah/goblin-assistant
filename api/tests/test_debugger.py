#!/usr/bin/env python3
"""
Test script for Raptor debugger integration
Run this to verify the integration works locally.
"""

import asyncio
import httpx
import os


async def test_debugger_endpoint():
    """Test the debugger endpoint with sample data"""

    # Test data
    test_cases = [
        {
            "task": "quick_fix",
            "context": {
                "error": "ValueError: division by zero",
                "code": "result = 10 / 0",
                "language": "python",
            },
        },
        {
            "task": "summarize_trace",
            "context": {
                "trace": "Traceback (most recent call last):\n  File 'app.py', line 5, in divide\n    return a / b\nZeroDivisionError: division by zero",
                "language": "python",
            },
        },
        {
            "task": "refactor_suggestion",  # Should route to fallback
            "context": {
                "code": "def old_function():\n    pass",
                "requirements": "Make it more modern",
            },
        },
    ]

    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n--- Test Case {i}: {test_case['task']} ---")
            try:
                response = await client.post(
                    "/debug/suggest", json=test_case, timeout=30
                )
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Success - Model: {data.get('model')}")
                    print(f"Suggestion: {data.get('suggestion')[:100]}...")
                    if "confidence" in data and data["confidence"] is not None:
                        print(f"Confidence: {data['confidence']}")
                else:
                    print(f"❌ Failed - Status: {response.status_code}")
                    print(f"Response: {response.text}")
            except Exception as e:
                print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("Testing Raptor Debugger Integration")
    print("=" * 40)

    # Check environment
    required_env = ["RAPTOR_URL", "FALLBACK_MODEL_URL"]
    missing = [env for env in required_env if not os.getenv(env)]
    if missing:
        print(f"⚠️  Missing environment variables: {', '.join(missing)}")
        print("Set them in .env.local or export them before running")
        exit(1)

    try:
        asyncio.run(test_debugger_endpoint())
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print(
            "Make sure the server is running: uvicorn apps.goblin_assistant.backend.main:app --reload --port 8000"
        )
