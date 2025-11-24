# ddtrace configuration for FastAPI
# This file configures ddtrace auto-instrumentation for the Goblin Assistant API

try:
    from ddtrace import patch_all, tracer, patch
    import os

    # Configure ddtrace agent connection via environment variables
    os.environ.setdefault("DD_AGENT_HOST", "localhost")
    os.environ.setdefault("DD_TRACE_AGENT_PORT", "8126")
    os.environ.setdefault("DD_ENV", "dev")
    os.environ.setdefault("DD_SERVICE", "goblin-assistant-api")
    os.environ.setdefault("DD_VERSION", "1.0.0")

    # Auto-instrument all supported libraries
    patch_all()

    # Additional patches for specific libraries
    patch(redis=True)  # Redis client
    patch(httpx=True)  # HTTP client
    patch(openai=True)  # OpenAI client

    # Custom tracer instance for manual instrumentation
    goblin_tracer = tracer

    # Configure DogStatsD client for custom metrics
    from datadog import initialize, statsd

    initialize(
        statsd_host=os.getenv("DD_AGENT_HOST", "localhost"),
        statsd_port=int(os.getenv("DD_DOGSTATSD_PORT", "8125")),
        statsd_namespace="goblin",
    )

    DDTRACE_AVAILABLE = True

except ImportError:
    # ddtrace not available, create dummy objects
    print("⚠️  ddtrace not available, running without Datadog tracing")

    class DummyTracer:
        def trace(self, *args, **kwargs):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class DummyStatsd:
        def increment(self, *args, **kwargs):
            pass

        def gauge(self, *args, **kwargs):
            pass

        def timing(self, *args, **kwargs):
            pass

    goblin_tracer = DummyTracer()
    statsd = DummyStatsd()
    DDTRACE_AVAILABLE = False

# Export for use in other modules
__all__ = ["goblin_tracer", "statsd", "DDTRACE_AVAILABLE"]
