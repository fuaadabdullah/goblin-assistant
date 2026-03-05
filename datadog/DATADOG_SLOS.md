# Datadog SLOs and Monitors for Goblin Assistant

This document defines Service Level Objectives (SLOs), Service Level Indicators (SLIs), and Datadog monitor configurations for the Goblin Assistant application.

## Service Level Objectives (SLOs)

### 1. API Response Time

**SLI**: 95th percentile response time for API endpoints
**SLO Target**: 95% of requests should complete within 2 seconds
**Time Window**: 30 days rolling
**Datadog Query**: `p95:trace.flask.request.duration{env:production,service:goblin-assistant} / 1000000`

### 2. API Error Rate

**SLI**: Percentage of API requests that return 5xx errors
**SLO Target**: Error rate should be less than 1%
**Time Window**: 7 days rolling
**Datadog Query**: `100 - (100 * sum:trace.flask.request.hits{env:production,service:goblin-assistant,status_code:2??}.as_count() / sum:trace.flask.request.hits{env:production,service:goblin-assistant}.as_count())`

### 3. Database Connection Health

**SLI**: Database connection pool utilization
**SLO Target**: Connection pool utilization should be below 80%
**Time Window**: 1 hour rolling
**Datadog Query**: `avg:db.connection_pool.utilization{env:production,db:postgres}`

### 4. Redis Memory Usage

**SLI**: Redis memory utilization
**SLO Target**: Memory usage should be below 85%
**Time Window**: 1 hour rolling
**Datadog Query**: `avg:redis.mem.used{env:production} / avg:redis.mem.maxmemory{env:production} * 100`

### 5. Cache Hit Rate

**SLI**: Redis cache hit rate
**SLO Target**: Cache hit rate should be above 90%
**Time Window**: 1 hour rolling
**Datadog Query**: `avg:redis.keyspace.hits{env:production} / (avg:redis.keyspace.hits{env:production} + avg:redis.keyspace.misses{env:production}) * 100`

## Datadog Monitors

### Critical Monitors (P1 - Page immediately)

#### 1. API 5xx Error Rate

```json
{
  "name": "Goblin Assistant - High API Error Rate",
  "type": "metric alert",
  "query": "sum(last_5m):sum:trace.flask.request.errors{env:production,service:goblin-assistant}.as_count() / sum:trace.flask.request.hits{env:production,service:goblin-assistant}.as_count() * 100 > 5",
  "message": "🚨 CRITICAL: API error rate is {{value}}% (threshold: 5%). Immediate investigation required.",
  "tags": ["team:goblin", "severity:critical", "service:goblin-assistant"],
  "options": {
    "notify_audit": false,
    "locked": false,
    "timeout_h": 0,
    "silenced": {},
    "include_tags": true,
    "no_data_timeframe": 10,
    "require_full_window": true,
    "notify_no_data": true,
    "renotify_interval": 0,
    "escalation_message": "",
    "thresholds": {
      "critical": 5,
      "warning": 2
    }
  }
}
```

#### 2. Database Connection Pool Exhausted

```json
{
  "name": "Goblin Assistant - Database Connection Pool Exhausted",
  "type": "metric alert",
  "query": "avg(last_5m):db.connection_pool.utilization{env:production,db:postgres} > 95",
  "message": "🚨 CRITICAL: Database connection pool is {{value}}% utilized. Risk of connection failures.",
  "tags": ["team:goblin", "severity:critical", "component:database"],
  "options": {
    "thresholds": {
      "critical": 95,
      "warning": 85
    }
  }
}
```

#### 3. Redis Memory Critical

```json
{
  "name": "Goblin Assistant - Redis Memory Critical",
  "type": "metric alert",
  "query": "avg(last_5m):redis.mem.used{env:production} / avg:redis.mem.maxmemory{env:production} * 100 > 95",
  "message": "🚨 CRITICAL: Redis memory usage is {{value}}%. Cache may fail.",
  "tags": ["team:goblin", "severity:critical", "component:redis"],
  "options": {
    "thresholds": {
      "critical": 95,
      "warning": 85
    }
  }
}
```

### Warning Monitors (P2 - Investigate within 30 minutes)

#### 4. API Response Time Degradation

```json
{
  "name": "Goblin Assistant - API Response Time High",
  "type": "metric alert",
  "query": "p95(last_10m):trace.flask.request.duration{env:production,service:goblin-assistant} / 1000000 > 5000",
  "message": "⚠️ WARNING: API p95 response time is {{value}}ms (threshold: 5000ms). User experience may be degraded.",
  "tags": ["team:goblin", "severity:warning", "component:api"],
  "options": {
    "thresholds": {
      "critical": 10000,
      "warning": 5000
    }
  }
}
```

#### 5. Cache Hit Rate Low

```json
{
  "name": "Goblin Assistant - Low Cache Hit Rate",
  "type": "metric alert",
  "query": "avg(last_15m):redis.keyspace.hits{env:production} / (avg:redis.keyspace.hits{env:production} + avg:redis.keyspace.misses{env:production}) * 100 < 80",
  "message": "⚠️ WARNING: Cache hit rate is {{value}}% (threshold: 80%). Performance may be degraded.",
  "tags": ["team:goblin", "severity:warning", "component:cache"],
  "options": {
    "thresholds": {
      "critical": 50,
      "warning": 80
    }
  }
}
```

#### 6. Database Backup Failed

```json
{
  "name": "Goblin Assistant - Database Backup Failed",
  "type": "event alert",
  "query": "events('source:github-actions status:error workflow:\"Database Backup\"').rollup('count').last('5m') > 0",
  "message": "⚠️ WARNING: Database backup workflow failed. Check GitHub Actions logs.",
  "tags": ["team:goblin", "severity:warning", "component:backup"],
  "options": {
    "thresholds": {
      "critical": 1
    }
  }
}
```

### Info Monitors (P3 - Track for trends)

#### 7. High Memory Usage

```json
{
  "name": "Goblin Assistant - High Memory Usage",
  "type": "metric alert",
  "query": "avg(last_5m):system.mem.used{env:production,host:goblin-*} / avg:system.mem.total{env:production,host:goblin-*} * 100 > 90",
  "message": "ℹ️ INFO: Memory usage is {{value}}% on {{host.name}}. Monitor for potential issues.",
  "tags": ["team:goblin", "severity:info", "component:system"],
  "options": {
    "thresholds": {
      "critical": 95,
      "warning": 90
    }
  }
}
```

## Dashboard Configuration

### Main Application Dashboard

Create a dashboard with the following widgets:

1. **API Performance**
   - Request rate (requests/second)
   - p95/p99 response times
   - Error rate percentage

2. **Database Metrics**
   - Connection pool utilization
   - Query latency
   - Active connections

3. **Cache Performance**
   - Hit/miss rates
   - Memory usage
   - Eviction rate

4. **System Resources**
   - CPU usage
   - Memory usage
   - Disk I/O

5. **Business Metrics**
   - Active users
   - Conversation count
   - Token usage by provider

## Alert Notification Channels

- **Critical (P1)**: Slack #goblin-alerts, email on-call, SMS
- **Warning (P2)**: Slack #goblin-alerts, email team
- **Info (P3)**: Slack #goblin-monitoring (no email)

## Implementation Notes

1. **Tags**: All metrics should be tagged with `env:production`, `service:goblin-assistant`, `team:goblin`
2. **Time Windows**: Use appropriate evaluation windows (5m, 10m, 15m) based on alert sensitivity
3. **Escalation**: Critical alerts should escalate if not acknowledged within 15 minutes
4. **Maintenance**: Schedule maintenance windows for deployments and updates
5. **Testing**: Regularly test alert configurations with synthetic monitors

## Related Documentation

- [PRODUCTION_MONITORING.md](../PRODUCTION_MONITORING.md) - Complete monitoring setup guide
- [PRODUCTION_DEPLOYMENT.md](../PRODUCTION_DEPLOYMENT.md) - Deployment procedures
- [Database Backup Automation](../scripts/backup/) - Backup scripts and procedures

