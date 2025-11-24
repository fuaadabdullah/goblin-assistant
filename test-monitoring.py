#!/usr/bin/env python3
"""
Test script to verify Datadog monitoring is working
Run this after setting up the agent and importing dashboard/monitors
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'api/fastapi'))

from metrics import metrics
from logging_config import logger
import time

def test_metrics():
    """Send test metrics to verify Datadog is receiving data"""
    print("📊 Testing Datadog metrics...")

    # Test basic metrics
    metrics.increment_counter("test.request.count", tags={"env": "dev", "service": "test"})
    metrics.histogram("test.request.latency_ms", 150.5, tags={"env": "dev", "service": "test"})
    metrics.gauge("test.queue.depth", 5, tags={"env": "dev", "service": "test"})

    # Test LLM-specific metrics
    metrics.record_llm_call("openai", "gpt-4o", tokens=150, cost_usd=0.002)
    metrics.record_provider_error("openai", "timeout")

    print("✅ Test metrics sent!")

def test_logging():
    """Send test logs to verify Datadog is receiving logs"""
    print("📝 Testing Datadog logging...")

    logger.info("Test log message", extra={"context": {"test": True, "user_id": "test-user"}})
    logger.warning("Test warning message", extra={"context": {"error_code": 500}})
    logger.error("Test error message", extra={"context": {"stack_trace": "test stack"}})

    print("✅ Test logs sent!")

def main():
    print("🧪 Testing Datadog monitoring setup...")
    print()

    test_metrics()
    print()

    test_logging()
    print()

    print("🎯 Test complete!")
    print("Check your Datadog dashboard in ~1-2 minutes to see the test data.")
    print("Look for metrics with 'service:test' tag.")

if __name__ == "__main__":
    main()
