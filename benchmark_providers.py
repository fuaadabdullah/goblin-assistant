#!/usr/bin/env python3
"""
Comprehensive benchmark script for AI providers in Goblin Assistant.
Tests latency, throughput, quality, and cost across all configured providers.
"""

import asyncio
import os
import sys
import time
import json
from typing import Dict, Any, List
from datetime import datetime
import statistics

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.providers.dispatcher import ProviderDispatcher


class ProviderBenchmark:
    """Benchmark AI providers for performance and quality."""

    def __init__(self):
        self.dispatcher = ProviderDispatcher()
        self.results: Dict[str, Any] = {}

        # Test prompts of varying complexity
        self.test_prompts = {
            "simple": {
                "prompt": "What is 2+2?",
                "expected_keywords": ["4", "four"],
                "max_tokens": 50,
            },
            "medium": {
                "prompt": "Explain what recursion is in programming in 2-3 sentences.",
                "expected_keywords": ["function", "calls", "itself"],
                "max_tokens": 150,
            },
            "code": {
                "prompt": "Write a Python function to calculate fibonacci numbers.",
                "expected_keywords": ["def", "fibonacci", "return"],
                "max_tokens": 300,
            },
            "reasoning": {
                "prompt": "If a train leaves Station A at 60mph and another leaves Station B 100 miles away at 40mph heading towards each other, when will they meet?",
                "expected_keywords": ["hour", "meet", "time"],
                "max_tokens": 200,
            },
        }

    async def benchmark_provider(
        self, provider_id: str, prompt_type: str = "simple", iterations: int = 3
    ) -> Dict[str, Any]:
        """Benchmark a single provider with multiple iterations."""
        print(f"\n🔧 Benchmarking {provider_id} with {prompt_type} prompt...")

        test_config = self.test_prompts[prompt_type]
        prompt = test_config["prompt"]

        latencies = []
        successful_runs = 0
        errors = []
        responses = []

        for i in range(iterations):
            try:
                provider = self.dispatcher.get_provider(provider_id)

                # Get default model for this provider
                config = self.dispatcher._get_provider_config(provider_id)
                model = config.get("default_model", "default")

                start = time.perf_counter()
                result = await provider.invoke(
                    prompt=prompt,
                    model=model,
                    stream=False,
                    max_tokens=test_config["max_tokens"],
                    temperature=0.2,
                )
                elapsed_ms = (time.perf_counter() - start) * 1000

                if result.get("ok"):
                    latencies.append(elapsed_ms)
                    successful_runs += 1
                    response_text = result.get("text", "")
                    responses.append(response_text)
                    print(f"   Run {i + 1}/{iterations}: {elapsed_ms:.2f}ms ✓")
                else:
                    error = result.get("error", "unknown")
                    errors.append(error)
                    print(f"   Run {i + 1}/{iterations}: FAILED ({error})")

            except Exception as e:
                errors.append(str(e))
                print(f"   Run {i + 1}/{iterations}: EXCEPTION ({str(e)})")

        # Calculate statistics
        if latencies:
            avg_latency = statistics.mean(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            p95_latency = (
                statistics.quantiles(latencies, n=20)[18]
                if len(latencies) >= 2
                else max_latency
            )

            # Check response quality (simple keyword matching)
            quality_score = self._assess_quality(
                responses, test_config["expected_keywords"]
            )

            return {
                "provider": provider_id,
                "success_rate": successful_runs / iterations,
                "avg_latency_ms": round(avg_latency, 2),
                "min_latency_ms": round(min_latency, 2),
                "max_latency_ms": round(max_latency, 2),
                "p95_latency_ms": round(p95_latency, 2),
                "quality_score": quality_score,
                "successful_runs": successful_runs,
                "total_runs": iterations,
                "errors": errors,
                "sample_response": responses[0] if responses else None,
            }
        else:
            return {
                "provider": provider_id,
                "success_rate": 0,
                "avg_latency_ms": 0,
                "errors": errors,
                "successful_runs": 0,
                "total_runs": iterations,
            }

    def _assess_quality(
        self, responses: List[str], expected_keywords: List[str]
    ) -> float:
        """Simple quality assessment based on keyword matching."""
        if not responses:
            return 0.0

        scores = []
        for response in responses:
            response_lower = response.lower()
            matched = sum(
                1 for keyword in expected_keywords if keyword.lower() in response_lower
            )
            score = matched / len(expected_keywords) if expected_keywords else 0
            scores.append(score)

        return round(statistics.mean(scores), 2) if scores else 0.0

    async def throughput_test(
        self, provider_id: str, duration_seconds: int = 10, concurrent_requests: int = 5
    ) -> Dict[str, Any]:
        """Test throughput with concurrent requests."""
        print(
            f"\n⚡ Throughput test for {provider_id} ({concurrent_requests} concurrent, {duration_seconds}s)..."
        )

        start_time = time.time()
        completed = 0
        errors = 0

        async def worker():
            nonlocal completed, errors
            while time.time() - start_time < duration_seconds:
                try:
                    provider = self.dispatcher.get_provider(provider_id)
                    config = self.dispatcher._get_provider_config(provider_id)
                    model = config.get("default_model", "default")

                    result = await provider.invoke(
                        prompt="Count from 1 to 5.",
                        model=model,
                        stream=False,
                        max_tokens=50,
                        temperature=0.1,
                    )

                    if result.get("ok"):
                        completed += 1
                    else:
                        errors += 1
                except Exception:
                    errors += 1

        # Run concurrent workers
        tasks = [worker() for _ in range(concurrent_requests)]
        await asyncio.gather(*tasks, return_exceptions=True)

        elapsed = time.time() - start_time
        throughput = completed / elapsed if elapsed > 0 else 0

        print(f"   Completed: {completed}, Errors: {errors}")
        print(f"   Throughput: {throughput:.2f} req/s")

        return {
            "completed": completed,
            "errors": errors,
            "duration_seconds": round(elapsed, 2),
            "throughput_req_per_sec": round(throughput, 2),
        }

    async def run_comprehensive_benchmark(self):
        """Run comprehensive benchmarks across all providers."""
        print("=" * 80)
        print("🚀 Goblin Assistant - AI Provider Benchmark Suite")
        print("=" * 80)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Define providers to test
        providers = [
            "openai",
            "anthropic",
            "groq",
            "siliconeflow",
            "gemini",
            "ollama_gcp",
            "llamacpp_gcp",
            "ollama",
        ]

        all_results = {}

        for provider_id in providers:
            print(f"\n{'=' * 80}")
            print(f"Testing Provider: {provider_id.upper()}")
            print(f"{'=' * 80}")

            try:
                # Test with simple prompt
                simple_results = await self.benchmark_provider(
                    provider_id, prompt_type="simple", iterations=3
                )

                # Test with medium complexity
                medium_results = await self.benchmark_provider(
                    provider_id, prompt_type="medium", iterations=2
                )

                # Throughput test (shorter duration for speed)
                throughput_results = await self.throughput_test(
                    provider_id, duration_seconds=5, concurrent_requests=3
                )

                all_results[provider_id] = {
                    "simple": simple_results,
                    "medium": medium_results,
                    "throughput": throughput_results,
                    "available": simple_results["success_rate"] > 0,
                }

                # Summary for this provider
                if simple_results["success_rate"] > 0:
                    print(f"\n✅ {provider_id}: WORKING")
                    print(f"   Average Latency: {simple_results['avg_latency_ms']}ms")
                    print(f"   Quality Score: {simple_results['quality_score']}")
                    print(
                        f"   Throughput: {throughput_results['throughput_req_per_sec']:.2f} req/s"
                    )
                else:
                    print(f"\n❌ {provider_id}: UNAVAILABLE")
                    if simple_results.get("errors"):
                        print(f"   Errors: {simple_results['errors']}")

            except Exception as e:
                print(f"\n❌ {provider_id}: EXCEPTION")
                print(f"   Error: {str(e)}")
                all_results[provider_id] = {"available": False, "error": str(e)}

        # Generate comparison report
        self._generate_comparison_report(all_results)

        # Save results to file
        self._save_results(all_results)

        return all_results

    def _generate_comparison_report(self, results: Dict[str, Any]):
        """Generate a comparison report across all providers."""
        print("\n" + "=" * 80)
        print("📊 BENCHMARK COMPARISON REPORT")
        print("=" * 80)

        # Available providers
        available = [p for p, r in results.items() if r.get("available")]
        unavailable = [p for p, r in results.items() if not r.get("available")]

        print(f"\n✅ Available Providers: {len(available)}/{len(results)}")

        if available:
            print(
                "\n┌─────────────────────┬──────────────┬──────────────┬──────────────┬────────────┐"
            )
            print(
                "│ Provider            │ Avg Latency  │ P95 Latency  │ Throughput   │ Quality    │"
            )
            print(
                "├─────────────────────┼──────────────┼──────────────┼──────────────┼────────────┤"
            )

            for provider_id in available:
                simple = results[provider_id].get("simple", {})
                throughput = results[provider_id].get("throughput", {})

                avg_lat = simple.get("avg_latency_ms", 0)
                p95_lat = simple.get("p95_latency_ms", 0)
                tp = throughput.get("throughput_req_per_sec", 0)
                quality = simple.get("quality_score", 0)

                print(
                    f"│ {provider_id:<19} │ {avg_lat:>10.2f}ms │ {p95_lat:>10.2f}ms │ {tp:>10.2f}rps │ {quality:>8.2f}   │"
                )

            print(
                "└─────────────────────┴──────────────┴──────────────┴──────────────┴────────────┘"
            )

        if unavailable:
            print(f"\n❌ Unavailable Providers: {len(unavailable)}")
            for provider_id in unavailable:
                error = results[provider_id].get("error", "Unknown error")
                print(f"   • {provider_id}: {error}")

        # Recommendations
        print("\n💡 Recommendations:")

        if available:
            # Find fastest provider
            fastest = min(
                available,
                key=lambda p: results[p]
                .get("simple", {})
                .get("avg_latency_ms", float("inf")),
            )
            fastest_latency = (
                results[fastest].get("simple", {}).get("avg_latency_ms", 0)
            )

            # Find highest throughput
            highest_tp_provider = max(
                available,
                key=lambda p: results[p]
                .get("throughput", {})
                .get("throughput_req_per_sec", 0),
            )
            highest_tp = (
                results[highest_tp_provider]
                .get("throughput", {})
                .get("throughput_req_per_sec", 0)
            )

            print(f"   🏎️  Fastest: {fastest} ({fastest_latency:.2f}ms avg latency)")
            print(
                f"   ⚡ Highest Throughput: {highest_tp_provider} ({highest_tp:.2f} req/s)"
            )

            # Cost-effectiveness check (prefer local/free providers)
            local_providers = [p for p in available if "ollama" in p or "llamacpp" in p]
            if local_providers:
                print(
                    f"   💰 Cost-Effective: {', '.join(local_providers)} (local/self-hosted)"
                )

        print("\n" + "=" * 80)

    def _save_results(self, results: Dict[str, Any]):
        """Save benchmark results to JSON file."""
        output_file = "benchmark_results.json"

        output_data = {"timestamp": datetime.now().isoformat(), "results": results}

        with open(output_file, "w") as f:
            json.dump(output_data, f, indent=2)

        print(f"\n💾 Results saved to: {output_file}")


async def main():
    """Main entry point."""
    benchmark = ProviderBenchmark()
    results = await benchmark.run_comprehensive_benchmark()

    # Check if any providers are available
    available_count = sum(1 for r in results.values() if r.get("available"))

    print(f"\n{'=' * 80}")
    print(f"Benchmark completed: {available_count}/{len(results)} providers available")
    print(f"{'=' * 80}\n")

    sys.exit(0 if available_count > 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
