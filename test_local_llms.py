#!/usr/bin/env python3
"""
Test script to verify local LLM deployments (Ollama and LlamaCPP).
Checks connectivity, available models, and basic inference.
"""

import asyncio
import os
import sys
import httpx
import time
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.providers.dispatcher_fixed import ProviderDispatcher


class LLMDeploymentTester:
    """Test local LLM deployments."""

    def __init__(self):
        self.dispatcher = ProviderDispatcher()
        self.results: Dict[str, Any] = {}

    async def test_endpoint_health(self, name: str, url: str) -> Dict[str, Any]:
        """Test basic connectivity to an endpoint."""
        print(f"\n🔍 Testing {name} at {url}")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                start = time.perf_counter()
                response = await client.get(
                    f"{url.rstrip('/')}/health", follow_redirects=True
                )
                elapsed_ms = (time.perf_counter() - start) * 1000

                if response.status_code == 200:
                    print(f"✅ {name} is healthy (responded in {elapsed_ms:.2f}ms)")
                    return {"ok": True, "latency_ms": elapsed_ms, "status": "healthy"}
                else:
                    print(f"⚠️  {name} returned status {response.status_code}")
                    return {"ok": False, "error": f"http-{response.status_code}"}

        except httpx.ConnectError:
            print(f"❌ {name} is unreachable (connection refused)")
            return {"ok": False, "error": "connection-refused"}
        except httpx.TimeoutException:
            print(f"❌ {name} timed out")
            return {"ok": False, "error": "timeout"}
        except Exception as e:
            print(f"❌ {name} error: {str(e)}")
            return {"ok": False, "error": str(e)}

    async def test_ollama_models(self, provider_id: str, endpoint: str) -> List[str]:
        """Get list of available Ollama models."""
        print(f"\n📋 Fetching models from {provider_id}")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{endpoint.rstrip('/')}/api/tags")

                if response.status_code == 200:
                    data = response.json()
                    models = [
                        model.get("name", "unknown") for model in data.get("models", [])
                    ]
                    print(f"✅ Found {len(models)} models: {', '.join(models)}")
                    return models
                else:
                    print(f"⚠️  Failed to fetch models: {response.status_code}")
                    return []

        except Exception as e:
            print(f"❌ Error fetching models: {str(e)}")
            return []

    async def test_llamacpp_models(self, provider_id: str, endpoint: str) -> List[str]:
        """Get list of available LlamaCPP models."""
        print(f"\n📋 Fetching models from {provider_id}")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{endpoint.rstrip('/')}/v1/models")

                if response.status_code == 200:
                    data = response.json()
                    models = [
                        model.get("id", "unknown") for model in data.get("data", [])
                    ]
                    print(f"✅ Found {len(models)} models: {', '.join(models)}")
                    return models
                else:
                    print(f"⚠️  Failed to fetch models: {response.status_code}")
                    return []

        except Exception as e:
            print(f"❌ Error fetching models: {str(e)}")
            return []

    async def test_inference(
        self, provider_id: str, model: str = None
    ) -> Dict[str, Any]:
        """Test inference with a provider."""
        print(f"\n🧪 Testing inference with {provider_id}")

        try:
            provider = self.dispatcher.get_provider(provider_id)

            # Use default model if not specified
            if model is None:
                config = self.dispatcher._get_provider_config(provider_id)
                model = config.get("default_model", "qwen2.5:latest")

            print(f"   Model: {model}")
            print(f"   Prompt: 'What is 2+2?'")

            start = time.perf_counter()
            result = await provider.invoke(
                prompt="What is 2+2? Answer with just the number.",
                model=model,
                stream=False,
                max_tokens=50,
                temperature=0.1,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000

            if result.get("ok"):
                text = result.get("text", "").strip()
                print(f"✅ Response: '{text}' (took {elapsed_ms:.2f}ms)")
                return {
                    "ok": True,
                    "response": text,
                    "latency_ms": elapsed_ms,
                    "model": result.get("model", model),
                }
            else:
                error = result.get("error", "unknown")
                print(f"❌ Inference failed: {error}")
                return {"ok": False, "error": error}

        except Exception as e:
            print(f"❌ Exception during inference: {str(e)}")
            return {"ok": False, "error": str(e)}

    async def run_tests(self):
        """Run all deployment tests."""
        print("=" * 70)
        print("🚀 Local LLM Deployment Verification")
        print("=" * 70)

        # Define test targets
        test_targets = [
            {
                "name": "Ollama GCP",
                "provider_id": "ollama_gcp",
                "url": os.getenv("OLLAMA_GCP_URL", "http://localhost:11434"),
                "type": "ollama",
            },
            {
                "name": "LlamaCPP GCP",
                "provider_id": "llamacpp_gcp",
                "url": os.getenv("LLAMACPP_GCP_URL", "http://localhost:8000"),
                "type": "llamacpp",
            },
            {
                "name": "Ollama Kamatera",
                "provider_id": "ollama_kamatera",
                "url": os.getenv("KAMATERA_SERVER2_URL", "http://192.175.23.150:8002"),
                "type": "ollama",
            },
            {
                "name": "LlamaCPP Kamatera",
                "provider_id": "llamacpp_kamatera",
                "url": os.getenv("KAMATERA_SERVER1_URL", "http://45.61.51.220:8000"),
                "type": "llamacpp",
            },
        ]

        for target in test_targets:
            print(f"\n{'=' * 70}")
            print(f"Testing: {target['name']}")
            print(f"{'=' * 70}")

            # Test health
            health = await self.test_endpoint_health(target["name"], target["url"])

            if health.get("ok"):
                # Fetch available models
                if target["type"] == "ollama":
                    models = await self.test_ollama_models(
                        target["provider_id"], target["url"]
                    )
                else:
                    models = await self.test_llamacpp_models(
                        target["provider_id"], target["url"]
                    )

                # Test inference with first available model
                if models:
                    inference = await self.test_inference(
                        target["provider_id"], models[0]
                    )
                else:
                    # Try with default model
                    inference = await self.test_inference(target["provider_id"])

                self.results[target["provider_id"]] = {
                    "name": target["name"],
                    "health": health,
                    "models": models,
                    "inference": inference,
                }
            else:
                self.results[target["provider_id"]] = {
                    "name": target["name"],
                    "health": health,
                    "models": [],
                    "inference": {"ok": False, "error": "endpoint-unhealthy"},
                }

        # Print summary
        print(f"\n{'=' * 70}")
        print("📊 Test Summary")
        print(f"{'=' * 70}")

        working = []
        failing = []

        for provider_id, result in self.results.items():
            name = result["name"]
            if result["health"].get("ok") and result["inference"].get("ok"):
                working.append(name)
                print(f"✅ {name}: WORKING")
            else:
                failing.append(name)
                error = result["health"].get("error") or result["inference"].get(
                    "error"
                )
                print(f"❌ {name}: FAILED ({error})")

        print(f"\n📈 Working: {len(working)}/{len(self.results)}")

        if working:
            print(f"\n🎉 The following deployments are operational:")
            for name in working:
                print(f"   • {name}")

        if failing:
            print(f"\n⚠️  The following deployments need attention:")
            for name in failing:
                print(f"   • {name}")

        return len(working) > 0


async def main():
    """Main entry point."""
    tester = LLMDeploymentTester()
    success = await tester.run_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
