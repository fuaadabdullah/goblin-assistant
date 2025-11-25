#!/usr/bin/env python3
"""
Test script to verify KPI metrics functionality.
"""

import sys
import os

sys.path.append(os.path.dirname(__file__))

from metrics import metrics


def test_kpi_metrics():
    """Test the new KPI metrics functionality."""
    print("🧪 Testing KPI Metrics Implementation")
    print("=" * 50)

    # Test assistant latency tracking
    print("✅ Testing assistant latency tracking...")
    metrics.record_assistant_latency("code_generation", 1250.5)
    metrics.record_assistant_latency("code_review", 890.2)

    # Test error rate tracking
    print("✅ Testing error rate tracking...")
    metrics.record_error_rate("api", 100, 2)  # 2% error rate
    metrics.record_error_rate("worker", 50, 1)  # 2% error rate

    # Test RAG hit rate tracking
    print("✅ Testing RAG hit rate tracking...")
    metrics.record_rag_hit_rate("code_generation", True)
    metrics.record_rag_hit_rate("code_review", False)
    metrics.record_rag_hit_rate("debugging", True)

    # Test fallback rate tracking
    print("✅ Testing fallback rate tracking...")
    metrics.record_fallback_rate("openai", False)
    metrics.record_fallback_rate("anthropic", True)
    metrics.record_fallback_rate("openai", False)

    # Test token usage tracking
    print("✅ Testing token usage tracking...")
    metrics.record_token_usage("openai", "gpt-4", 1500)
    metrics.record_token_usage("anthropic", "claude-3", 1200)

    # Test cost tracking
    print("✅ Testing cost tracking...")
    metrics.record_cost_tracking("openai", 0.045)
    metrics.record_cost_tracking("anthropic", 0.032)

    # Test code acceptance tracking
    print("✅ Testing code acceptance tracking...")
    metrics.record_code_acceptance(True, "code_generation")
    metrics.record_code_acceptance(False, "code_review")
    metrics.record_code_acceptance(True, "debugging")

    # Test queue alert tracking
    print("✅ Testing queue alert tracking...")
    metrics.record_queue_alert("mcp:queue", 45)  # Below threshold
    metrics.record_queue_alert("mcp:queue", 55)  # Above threshold - should alert

    print("✅ All KPI metrics recorded successfully!")
    print("\n📊 Expected Datadog Metrics:")
    print("   • assistant.latency_ms (p95 tracking)")
    print("   • error.rate_percent")
    print("   • rag.context_usage")
    print("   • provider.fallbacks")
    print("   • token.usage")
    print("   • cost.daily_usd")
    print("   • code.acceptance")
    print("   • queue.depth + queue.alert")

    return True


if __name__ == "__main__":
    try:
        test_kpi_metrics()
        print("\n🎉 KPI Metrics Test Completed Successfully!")
    except Exception as e:
        print(f"\n❌ KPI Metrics Test Failed: {e}")
        sys.exit(1)
