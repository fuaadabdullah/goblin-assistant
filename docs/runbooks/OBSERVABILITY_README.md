---
title: "OBSERVABILITY README"
description: "Goblin Assistant OpenTelemetry Observability Setup"
---

# Goblin Assistant OpenTelemetry Observability Setup

This document describes the comprehensive OpenTelemetry instrumentation implemented for the Goblin Assistant application to address observability gaps and unify monitoring systems.

## Overview

The observability stack includes:

- **OpenTelemetry**: Unified tracing, metrics, and logging
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization and dashboards
- **Jaeger**: Distributed tracing
- **Cloudflare Workers**: Edge observability with trace propagation

## Architecture

```text
Cloudflare Workers (Edge)
    ↓ (W3C Trace Context)
Backend (FastAPI)
    ↓ (OTLP)
OTLP Collector
    ↓
├── Prometheus (Metrics)
├── Jaeger (Traces)
└── Loki (Logs)
    ↓
Grafana (Visualization)
```

## Components

### 1. OpenTelemetry Configuration (`opentelemetry_config.py`)

- Initializes OpenTelemetry SDK with OTLP exporters
- Auto-instrumentation for FastAPI, HTTPX, SQLAlchemy, Redis
- Custom metrics and trace instrumentation
- Environment-based configuration

### 2. SLO Definitions (`monitoring/slos.py`)

Service Level Objectives:

- **Chat Response Time**: P95 < 2 seconds
- **Auth Success Rate**: > 99.9%
- **LLM Availability**: > 99.5%
- **API Availability**: > 99.9%

### 3. Business Metrics (`monitoring/business_metrics.py`)

Key Performance Indicators:

- Daily/Monthly Active Users
- Cost per request
- Provider usage analytics
- Conversation metrics

### 4. Unified Metrics (`monitoring/metrics.py`)

- Bridges Prometheus and OpenTelemetry metrics
- Custom counters, histograms, and gauges
- SLO compliance tracking

### 5. Enhanced Logging (`middleware/logging_middleware.py`)

- Trace context integration
- Structured logging with correlation IDs
- Error tracking and debugging

### 6. Cloudflare Worker (`infra/cloudflare/worker.js`)

- Intelligent LLM routing
- W3C Trace Context propagation
- Bot protection and rate limiting
- Edge-level observability

### 7. OTLP Collector (`infra/otel-collector-config.yaml`)

- Receives telemetry data from backend
- Exports to Prometheus, Jaeger, Loki
- Data processing and filtering

### 8. Alerting Rules (`infra/alert_rules.yml`)

Prometheus alerting rules for:

- SLO violations
- Error rate thresholds
- Performance degradation
- Service availability

### 9. Grafana Dashboard (`infra/grafana-dashboard.json`)

Comprehensive dashboard showing:

- SLO compliance overview
- Response time percentiles
- Request rates and error rates
- Business metrics
- Trace spans and service health

## Deployment

### Prerequisites

- Docker and Docker Compose
- Terraform
- Cloudflare Wrangler CLI
- Python 3.8+

### Production Deployment

Run the automated deployment script:

```bash

chmod +x deploy_observability.sh
./deploy_observability.sh
```

This script will:

1. Deploy OTLP Collector
2. Deploy Cloudflare Worker
3. Enable OpenTelemetry in backend
4. Deploy monitoring stack (Prometheus, Grafana, Jaeger)
5. Configure alerting rules
6. Validate deployment

### Manual Deployment Steps

1. **Start OTLP Collector:**

   ```bash
   cd goblin-infra/projects/goblin-assistant/infra
   docker-compose up -d otel-collector
   ```

2. **Deploy Cloudflare Worker:**

   ```bash

   cd goblin-infra/projects/goblin-assistant/infra/cloudflare
   wrangler deploy
   ```

3. **Enable OpenTelemetry in Backend:**

   ```bash
   export ENABLE_OPENTELEMETRY=true
   # Or add to .env file: ENABLE_OPENTELEMETRY=true
   ```

4. **Deploy Monitoring Stack:**

   ```bash

   cd goblin-infra/projects/goblin-assistant/infra
   docker-compose up -d prometheus grafana jaeger
   ```

5. **Configure Alerting:**

   ```bash
   docker cp alert_rules.yml goblin-infra_prometheus_1:/etc/prometheus/
   docker exec goblin-infra_prometheus_1 kill -HUP 1
   ```

## Monitoring URLs

After deployment, access these services:

- **Grafana**: <http://localhost:3000> (admin/admin)
- **Prometheus**: <http://localhost:9090>
- **Jaeger**: <http://localhost:16686>
- **Cloudflare Worker**: <https://goblin-assistant-edge.fuaadabdullah.workers.dev>

## Key Features

### Distributed Tracing

- End-to-end trace propagation from Cloudflare Workers to LLM providers
- Automatic instrumentation for all HTTP requests
- Custom spans for business logic
- Correlation IDs for log tracing

### SLO-Based Monitoring

- Real-time SLO compliance tracking
- Automated alerting on SLO violations
- Historical compliance analysis
- Error budget tracking

### Business Metrics

- User engagement metrics (DAU/MAU)
- Cost optimization insights
- Provider performance comparison
- Conversation analytics

### Alerting

- SLO violation alerts
- Error rate monitoring
- Performance degradation alerts
- Service availability alerts

## Configuration

### Environment Variables

```bash

# Enable OpenTelemetry
ENABLE_OPENTELEMETRY=true

# OTLP Collector endpoint
OTEL_EXPORTER_OTLP_ENDPOINT=<http://localhost:4318>

# Service identification
OTEL_SERVICE_NAME=goblin-assistant-backend
OTEL_SERVICE_VERSION=1.0.0

# Tracing configuration
OTEL_TRACES_EXPORTER=otlp
OTEL_METRICS_EXPORTER=otlp
OTEL_LOGS_EXPORTER=otlp
```

### SLO Configuration

SLOs are defined in `monitoring/slos.py` and can be adjusted:

```python
CHAT_RESPONSE_TIME_SLO = 2.0  # seconds
AUTH_SUCCESS_RATE_SLO = 0.999  # 99.9%
LLM_AVAILABILITY_SLO = 0.995   # 99.5%
API_AVAILABILITY_SLO = 0.999   # 99.9%
```

## Troubleshooting

### Common Issues

1. **OTLP Collector not receiving data:**
   - Check network connectivity between backend and collector
   - Verify OTLP endpoint configuration
   - Check collector logs: `docker logs otel-collector`

2. **Missing traces in Jaeger:**
   - Ensure trace context propagation is working
   - Check sampling rates
   - Verify OTLP exporter configuration

3. **Prometheus metrics not appearing:**
   - Check OTLP collector to Prometheus pipeline
   - Verify metric names and labels
   - Check Prometheus targets status

4. **Grafana dashboard not loading:**
   - Import dashboard JSON manually
   - Check Prometheus data source configuration
   - Verify dashboard JSON syntax

### Debugging

Enable debug logging:

```bash

export OTEL_LOG_LEVEL=DEBUG
export OTEL_PYTHON_LOGGING_LEVEL=DEBUG
```

Check service logs:

```bash
# OTLP Collector
docker logs otel-collector

# Prometheus
docker logs prometheus

# Grafana
docker logs grafana

# Jaeger
docker logs jaeger
```

## Performance Impact

The OpenTelemetry instrumentation adds minimal overhead:

- CPU: < 5% increase
- Memory: < 50MB increase
- Network: OTLP data export (configurable batching)

## Security Considerations

- OTLP data is sent over HTTP (use TLS in production)
- Sensitive data is not included in telemetry
- Cloudflare Workers handle edge security
- Access controls on monitoring services

## Future Enhancements

- Integration with Datadog for production monitoring
- Advanced anomaly detection
- Cost optimization recommendations
- Automated incident response
- Multi-region observability

## Support

For issues or questions:

1. Check the troubleshooting section
2. Review service logs
3. Validate configuration
4. Check OpenTelemetry documentation

## Contributing

When adding new features:

1. Include OpenTelemetry instrumentation
2. Add relevant metrics and traces
3. Update SLOs if needed
4. Test observability in development
5. Update documentation
