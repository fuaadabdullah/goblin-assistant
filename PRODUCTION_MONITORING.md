---
title: "PRODUCTION MONITORING"
description: "Production Configuration Guide"
---

This document has moved into the canonical backend documentation folder:

- apps/goblin-assistant/backend/docs/PRODUCTION_MONITORING.md

Please update any references or links to point to the new location.

# Production Configuration Guide

## Environment Variables

Add these to your `backend/.env` file:

```bash
# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# CORS Configuration (comma-separated list)
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com,https://www.yourdomain.com

# Rate Limiting (optional, defaults in rate_limiter.py)
# RATELIMIT_ENABLED=true
```

## Middleware Features

### 1. Rate Limiting (slowapi)

**Default Limits:**

- Auth endpoints: 10 requests/minute
- Chat endpoints: 30 requests/minute
- Health endpoints: 60 requests/minute
- General API: 100 requests/minute

**How it works:**

- Tracks by client IP address
- Returns 429 status when exceeded
- Includes `retry_after` in response

**Response format:**

```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded: 10 per 1 minute",
  "retry_after": 45
}
```

### 2. Structured JSON Logging

**Features:**

- All logs in JSON format for easy parsing
- Automatic request/response logging
- Correlation IDs for request tracing
- Error tracking with stack traces

**Log format:**

```json
{
  "timestamp": "2025-12-02T10:30:45.123Z",
  "level": "INFO",
  "logger": "goblin_assistant",
  "message": "request_completed",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "POST",
  "path": "/chat/completions",
  "status_code": 200,
  "duration_ms": 1234.56
}
```

**Correlation ID:**

- Added to every request automatically
- Returned in `X-Correlation-ID` response header
- Use for debugging across distributed systems

### 3. Prometheus Metrics

**Metrics endpoint:** `GET /metrics`

**Available metrics:**

```prometheus

# HTTP Metrics
http_requests_total{method="POST",endpoint="/chat/completions",status_code="200"} 42
http_request_duration_seconds_bucket{method="POST",endpoint="/chat/completions",le="1.0"} 35
http_requests_in_progress{method="POST",endpoint="/chat/completions"} 2
http_errors_total{method="POST",endpoint="/chat/completions",error_type="TimeoutError"} 1

# Business Metrics
chat_completions_total{provider="openai",model="gpt-4"} 100
chat_completion_tokens_total{provider="openai",model="gpt-4",token_type="prompt"} 50000
chat_completion_errors_total{provider="anthropic",error_type="rate_limit"} 5
provider_latency_seconds{provider="openai",operation="chat_completion"} 1.234

# Health Metrics
service_health_status{service_name="chroma"} 1
service_health_status{service_name="sandbox"} 0
```

**Custom metric tracking in code:**

```python
from middleware.metrics import (
    chat_completions_total,
    chat_completion_tokens_total,
    provider_latency_seconds
)

# Track completion
chat_completions_total.labels(
    provider="openai",
    model="gpt-4"
).inc()

# Track tokens
chat_completion_tokens_total.labels(
    provider="openai",
    model="gpt-4",
    token_type="prompt"
).inc(response.usage.prompt_tokens)

# Track latency
provider_latency_seconds.labels(
    provider="openai",
    operation="chat_completion"
).observe(duration)
```

### 4. Load Testing (Locust)

**Run load tests:**

```bash

# Install dependencies
pip install -r backend/requirements.txt

# Start backend
cd apps/goblin-assistant/backend
uvicorn main:app --host 0.0.0.0 --port 8001

# Run load test with Web UI
locust -f backend/tests/load_test.py --host=<http://localhost:8001>

# Open browser to http://localhost:8089

# Set number of users and spawn rate

# Headless mode (CLI only)
locust -f backend/tests/load_test.py --host=<http://localhost:8001> \
       --users 10 --spawn-rate 2 --run-time 60s --headless
```

**Performance targets:**

- Health checks: < 100ms p95, 100 RPS
- Chat completions: < 2s p95, 10 RPS
- Auth login: < 500ms p95, 20 RPS

**Test scenarios:**

1. `health_check` (10x weight) - Basic health endpoint
2. `health_all` (8x) - Detailed health with all services
3. `health_chroma` (5x) - ChromaDB health check
4. `health_sandbox` (3x) - Sandbox health check
5. `get_models` (2x) - List available models
6. `chat_completion` (1x) - Full chat completion (expensive)
7. `get_settings` (2x) - Retrieve settings
8. `login` (1x) - Authentication

## Monitoring Setup

### Prometheus + Grafana

**1. Install Prometheus:**

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'goblin-assistant'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8001']
```

**2. Install Grafana:**

```bash

# Add Prometheus as data source in Grafana

# URL: http://localhost:9090

# Import dashboard or create custom:

# - Request rate by endpoint

# - Error rate by endpoint

# - P95 latency by endpoint

# - Active requests gauge

# - Chat completion metrics
```

### Alerting Rules

**Example Prometheus alerts:**

```yaml
groups:
  - name: goblin_assistant_alerts
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: rate(http_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: 'High error rate detected'
          description: 'Error rate is {{ $value }} errors/sec'

      # Slow response time
      - alert: SlowResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: 'Slow API response time'
          description: 'P95 latency is {{ $value }}s'

      # Service down
      - alert: ServiceUnhealthy
        expr: service_health_status == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: 'Service {{ $labels.service_name }} is unhealthy'

      # High chat completion errors
      - alert: HighChatCompletionErrors
        expr: rate(chat_completion_errors_total[5m]) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: 'High chat completion error rate'
          description: 'Provider {{ $labels.provider }}: {{ $value }} errors/sec'
```

### Log Aggregation

**Option 1: ELK Stack (Elasticsearch, Logstash, Kibana)**

```bash

# Logs are already in JSON format

# Configure Logstash to ingest from stdout/file

# Query in Kibana using correlation_id, method, path, etc.
```

**Option 2: Datadog**

```bash
# Install Datadog agent
DD_API_KEY=<your_key> DD_SITE="datadoghq.com" bash -c "$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script.sh)"

# Configure log collection
# Datadog automatically parses JSON logs
```

**Option 3: CloudWatch (AWS)**

```bash

# Use awslogs driver for Docker

# Or install CloudWatch agent for direct logging
```

## Deployment Checklist

- [ ] Set `CORS_ORIGINS` to production domains
- [ ] Set `LOG_LEVEL=INFO` (or WARNING for production)
- [ ] Configure Prometheus scraping
- [ ] Set up Grafana dashboards
- [ ] Configure alerting rules
- [ ] Set up log aggregation
- [ ] Run load tests on staging
- [ ] Set up automated health checks
- [ ] Configure rate limit thresholds for your scale
- [ ] Monitor metrics for first 24 hours

## Testing the Setup

**1. Check rate limiting:**

```bash
# Should return 429 after 10 requests
for i in {1..15}; do
  curl -X POST http://localhost:8001/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"test"}'
  sleep 1
done
```

**2. Check structured logs:**

```bash

# Start server and watch logs
uvicorn main:app --host 0.0.0.0 --port 8001 | jq

# Should see JSON formatted logs with correlation_id
```

**3. Check Prometheus metrics:**

```bash
curl http://localhost:8001/metrics

# Should see Prometheus format:
# http_requests_total{...} 42
# http_request_duration_seconds_bucket{...} 35
```

**4. Run load test:**

```bash

locust -f backend/tests/load_test.py --host=<http://localhost:8001> \
       --users 10 --spawn-rate 2 --run-time 30s --headless

# Should complete without errors

# Check that performance targets are met
```

## Production Recommendations

1. **Rate Limiting:**
   - Tune limits based on your infrastructure
   - Consider Redis-based rate limiting for distributed systems
   - Add API key-based limits (not just IP)

2. **Logging:**
   - Send logs to centralized aggregation service
   - Set log retention policies
   - Create alerts on ERROR level logs

3. **Metrics:**
   - Set up automated alerts in Prometheus/Grafana
   - Create dashboards for real-time monitoring
   - Track business metrics (token usage, costs, etc.)

4. **Load Testing:**
   - Run regular load tests on staging
   - Test disaster recovery scenarios
   - Validate auto-scaling configuration

5. **Security:**
   - Enable HTTPS in production
   - Use reverse proxy (nginx/traefik) for additional protection
   - Implement API key authentication for sensitive endpoints
   - Add request size limits
   - Enable CORS only for trusted origins

### Privacy & Vector DB / RAG (Guidance)

- Do NOT embed PII or secrets into vector stores (Chroma) or include them in prompts to third-party LLM providers. Sanitize and check consent before creating embeddings.
- Apply TTLs for conversation context and vector DB entries, and implement automated purge or deletion paths for sensitive data.
- Store only hashed/anonymized metadata in logs; avoid logging raw user messages or secrets. If a snippet is necessary for debugging, mask or pseudonymize it and keep it under strict access controls.
