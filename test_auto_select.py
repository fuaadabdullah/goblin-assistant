import asyncio
import sys
import os

# Add the API directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "api"))

from api.providers.dispatcher_fixed import dispatcher


async def test_auto_select():
    print("🧪 Testing Auto-Provider Selection")

    # Ensure LOCAL_LLM_API_KEY is available for the test environment
    os.environ["LOCAL_LLM_API_KEY"] = (
        "cef5587890c73a5316a9a2c4ed851d97beb89fd28443885aad6e570dabd5f765"
    )

    result = await dispatcher.invoke_provider(
        provider_id=None,
        model="qwen2.5:latest",
        payload={"messages": [{"role": "user", "content": "Hello!"}]},
        timeout_ms=30000,
        stream=False,
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(test_auto_select())
