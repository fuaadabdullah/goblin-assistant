#!/usr/bin/env python3
"""
Llama Model Validation Script for Goblin Assistant
Tests local Llama models for quality and coherence.
"""

import sys
import os
import json
import time
import requests
from typing import Dict, List, Optional
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class LlamaValidator:
    """Validates Llama models running on llama.cpp server."""

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.timeout = 30

    def check_server_health(self) -> bool:
        """Check if llama.cpp server is responding."""
        try:
            response = self.session.get(f"{self.base_url}/health")
            return response.status_code == 200
        except requests.RequestException:
            return False

    def get_model_info(self) -> Optional[Dict]:
        """Get information about the loaded model."""
        try:
            response = self.session.get(f"{self.base_url}/props")
            if response.status_code == 200:
                return response.json()
        except requests.RequestException:
            pass
        return None

    def test_completion(self, prompt: str, max_tokens: int = 100) -> Optional[str]:
        """Test text completion with the model."""
        try:
            data = {
                "prompt": prompt,
                "n_predict": max_tokens,
                "temperature": 0.7,
                "top_k": 40,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
            }

            response = self.session.post(
                f"{self.base_url}/completion",
                json=data,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("content", "").strip()

        except requests.RequestException as e:
            print(f"Request failed: {e}")
        except json.JSONDecodeError as e:
            print(f"Invalid JSON response: {e}")

        return None

    def analyze_response_quality(self, response: str) -> Dict[str, float]:
        """Analyze the quality of a model response."""
        if not response:
            return {"score": 0.0, "coherence": 0.0, "relevance": 0.0, "garbled": True}

        # Check for garbled output (common issue with corrupted models)
        garbled_chars = [
            "\x1c",
            "\x00",
            "\x01",
            "\x02",
            "\x03",
            "\x04",
            "\x05",
            "\x06",
            "\x07",
            "\x08",
            "\x0b",
            "\x0c",
            "\x0e",
            "\x0f",
            "\x10",
            "\x11",
            "\x12",
            "\x13",
            "\x14",
            "\x15",
            "\x16",
            "\x17",
            "\x18",
            "\x19",
            "\x1a",
            "\x1b",
            "\x1d",
            "\x1e",
            "\x1f",
        ]
        garbled_ratio = (
            sum(1 for char in response if char in garbled_chars) / len(response)
            if response
            else 0
        )

        # Basic quality metrics
        coherence = 1.0 if len(response.split()) > 5 else 0.5
        relevance = (
            1.0 if "@" not in response and garbled_ratio < 0.1 else 0.0
        )  # Check for garbled output

        # Overall score (0-1 scale)
        score = (coherence + relevance) / 2.0

        return {
            "score": score,
            "coherence": coherence,
            "relevance": relevance,
            "garbled": garbled_ratio > 0.1,
            "garbled_ratio": garbled_ratio,
        }


def main():
    parser = argparse.ArgumentParser(description="Validate Llama models")
    parser.add_argument(
        "--url", default="http://localhost:8080", help="llama.cpp server URL"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    print("🧠 Llama Model Validation")
    print("=" * 40)

    validator = LlamaValidator(args.url)

    # Check server health
    print(f"🔍 Checking server at {args.url}...")
    if not validator.check_server_health():
        print("❌ Server is not responding")
        return 1

    print("✅ Server is healthy")

    # Get model info
    model_info = validator.get_model_info()
    if model_info:
        print(f"📋 Model: {model_info.get('model', 'Unknown')}")
        print(f"📏 Context size: {model_info.get('n_ctx', 'Unknown')}")
    else:
        print("⚠️  Could not retrieve model information")

    # Test prompts
    test_prompts = [
        "Hello, how are you?",
        "What is the capital of France?",
        "Explain quantum computing in simple terms.",
        "Write a short poem about AI.",
    ]

    print("\n🧪 Testing model responses...")
    print("-" * 40)

    total_score = 0.0
    test_count = 0

    for i, prompt in enumerate(test_prompts, 1):
        print(f"\nTest {i}: {prompt}")
        print("-" * 20)

        response = validator.test_completion(prompt)
        if response:
            # Truncate long responses for display
            display_response = (
                response[:200] + "..." if len(response) > 200 else response
            )
            print(f"Response: {display_response}")

            quality = validator.analyze_response_quality(response)
            print(".2f")
            print(".2f")
            print(".2f")
            if quality.get("garbled", False):
                print(".1%")
                print("⚠️  WARNING: High garbled character ratio detected!")
            else:
                print("✅ No garbled output detected")

            total_score += quality["score"]
            test_count += 1
        else:
            print("❌ No response received")
            total_score += 0.0
            test_count += 1

    # Overall assessment
    print("\n📊 Validation Results")
    print("-" * 40)

    if test_count > 0:
        avg_score = total_score / test_count
        print(".2f")

        if avg_score >= 0.8:
            print("🎉 Model quality: EXCELLENT")
            print("✅ Model is production-ready")
        elif avg_score >= 0.6:
            print("👍 Model quality: GOOD")
            print("✅ Model is usable but could be improved")
        elif avg_score >= 0.4:
            print("⚠️  Model quality: FAIR")
            print("🔄 Consider different quantization or model")
        else:
            print("❌ Model quality: POOR")
            print("🚫 Model needs replacement or retraining")

        # Check for garbled output issues
        garbled_tests = sum(
            1
            for prompt in test_prompts
            if validator.analyze_response_quality(
                validator.test_completion(prompt) or ""
            ).get("garbled", False)
        )

        if garbled_tests > 0:
            print(
                f"🚨 CRITICAL: {garbled_tests}/{len(test_prompts)} tests produced garbled output"
            )
            print("💡 This usually indicates:")
            print("   - Corrupted or incompatible model file")
            print("   - Wrong quantization format")
            print("   - Model trained on different data format")
            print("   - Try a different model or source")

        return 0 if avg_score >= 0.6 and garbled_tests == 0 else 1
    else:
        print("❌ No tests completed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
