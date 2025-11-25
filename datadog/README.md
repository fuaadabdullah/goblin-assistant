# Datadog Monitoring Setup for Goblin Assistant

This directory contains the complete Datadog monitoring configuration for the Goblin Assistant MCP service, including monitors, dashboards, and setup scripts.

## 📊 KPI Monitoring

The following production KPIs are monitored with automated alerts:

### Core Performance Metrics

- **P95 Response Latency**: < 1.5 seconds (Critical: >1.5s, Warning: >1s)
- **Error Rate**: < 3% (Critical: >3%, Warning: >1%)
- **Queue Depth**: < 50 requests (Critical: >50, Warning: >25)

### AI/ML Performance Metrics

- **RAG Hit Rate**: > 60% for code tasks (Critical: <60%, Warning: <70%)
- **Provider Fallback Rate**: < 5% per 1k requests (Critical: >5%, Warning: >2%)

### Cost & Usage Metrics

- **Daily Cost**: < $50/day (Warning: >$25, Critical: >$50)
- **Token Usage**: Per-provider tracking
- **Code Acceptance Rate**: Success rate tracking

## 🚀 Quick Start

### 1. Environment Setup

Copy the environment template and add your Datadog credentials:

```bash
cp .env.example .env
# Edit .env with your Datadog API keys
```

Required environment variables:

```bash
DD_API_KEY=your_datadog_api_key
DD_APP_KEY=your_datadog_app_key
DD_SITE=datadoghq.com  # or datadoghq.eu for EU region
ENV=production
POSTGRES_PASSWORD=your_secure_password
```

### 2. Deploy with Docker

Start all services including Datadog agent:

```bash
docker-compose up -d
```

This will start:

- **Datadog Agent**: Metrics collection and forwarding
- **Goblin Assistant**: Main application with monitoring
- **PostgreSQL**: Database
- **Redis**: Queue and caching

### 3. Setup Monitors & Dashboard

Run the automated setup script:

```bash
chmod +x setup-datadog.sh
./setup-datadog.sh
```

This will:

- ✅ Test Datadog API connection
- 📊 Create all KPI monitors
- 📈 Create the production dashboard

## 📈 Dashboard

The production dashboard (`datadog/dashboard.json`) includes:

- **P95 Response Latency** with threshold lines
- **Error Rate %** with alerting thresholds
- **RAG Hit Rate %** for context usage
- **Provider Fallback Rate %** for reliability
- **Queue Depth** with capacity alerts
- **Daily Cost ($)** with budget tracking
- **Request Volume** and **Token Usage** trends

## 📊 Monitors

### Monitor Files (`datadog/monitors/`)

1. **`latency-monitor.json`**: P95 response latency alerts
2. **`error-rate-monitor.json`**: Error rate percentage alerts
3. **`rag-hit-rate-monitor.json`**: RAG context usage alerts
4. **`fallback-rate-monitor.json`**: Provider fallback alerts
5. **`queue-depth-monitor.json`**: Queue capacity alerts
6. **`daily-cost-monitor.json`**: Cost budget alerts

### Alert Configuration

All monitors include:

- **Priority levels**: P1 (Critical), P2 (Warning), P3 (Info)
- **Notification settings**: Slack alerts, email notifications
- **Auto-resolution**: Monitors resolve automatically when thresholds normalize
- **Evaluation delays**: Prevent false alerts during deployments

## 🔧 Manual Setup (Alternative)

If you prefer manual setup:

### Create Monitors Manually

1. Go to Datadog Monitors → New Monitor
2. Select "Metric" monitor type
3. Use the queries from the JSON files
4. Configure alerts and notifications

### Import Dashboard

1. Go to Datadog Dashboards → New Dashboard
2. Import JSON from `datadog/dashboard.json`
3. Adjust queries for your environment tags

## 📋 Monitoring Endpoints

### Admin Dashboard

```http
GET /mcp/v1/admin/dashboard
```

Returns real-time KPI metrics and system status.

### Health Check

```http
GET /api/health
```

Basic service health check.

### Provider Status

```http
GET /mcp/v1/providers/status
```

Current provider health and circuit breaker status.

## 🔍 Troubleshooting

### Metrics Not Appearing

1. Check Datadog agent logs:

   ```bash
   docker-compose logs datadog
   ```

2. Verify environment variables:

   ```bash
   docker-compose exec goblin-assistant env | grep DD_
   ```

3. Test metrics manually:

   ```bash
   docker-compose exec datadog datadog-agent status
   ```

### Alerts Not Working

1. Verify monitor queries in Datadog UI
2. Check notification channels are configured
3. Test with manual alert triggers

### High Latency Issues

1. Check queue depth: `GET /mcp/v1/admin/dashboard`
2. Monitor provider latency: Datadog dashboard
3. Check database performance: PostgreSQL logs
4. Scale workers if needed

## 📚 Additional Resources

- [Datadog Documentation](https://docs.datadoghq.com/)
- [Datadog API Reference](https://docs.datadoghq.com/api/latest/)
- [Docker Compose Monitoring](https://docs.datadoghq.com/containers/docker/)

## 🎯 Production Checklist

- [ ] Datadog API keys configured
- [ ] Docker services running
- [ ] Monitors created and alerting
- [ ] Dashboard imported and customized
- [ ] Notification channels configured
- [ ] Alert thresholds tested
- [ ] Backup monitoring (PagerDuty, OpsGenie)

---

**Last Updated**: November 24, 2025
**Version**: 1.0.0
