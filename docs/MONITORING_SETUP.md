---
title: "MONITORING SETUP"
description: "Simplified Observability & Monitoring Setup"
---

# Simplified Observability & Monitoring Setup

## Overview

Goblin Assistant uses a **lightweight, production-ready monitoring stack** optimized for <100k users. We've removed excessive tooling (Datadog, Prometheus, Loki, Tempo, OpenTelemetry) in favor of essential, cost-effective solutions.

## Current Stack

### ✅ ERRORS & CRASHES

- **Sentry** ($26/month)
  - Frontend: `@sentry/react` with performance monitoring
  - Backend: `sentry-sdk[fastapi]` with SQLAlchemy/Redis integration
  - Captures: exceptions, stack traces, user context, performance traces

### ✅ APPLICATION METRICS

- **Fly.io built-in metrics** (free)
  - Response time, throughput, memory, CPU
  - View at: `fly.io dashboard → Monitoring`
- **Vercel Analytics** (free)
  - Page views, user sessions, performance metrics
  - View at: `vercel.com dashboard → Analytics`

### ✅ LOGGING

- **Fly.io logs** (free)
  - `fly logs` - Real-time application logs
  - Structured JSON logging with correlation IDs
- **Vercel logs** (free)
  - Built-in request/response logging
  - Error tracking and performance insights

### ✅ UPTIME MONITORING

- **UptimeRobot** (free tier: 50 monitors)
  - Monitor API endpoints and frontend
  - Email/SMS alerts for downtime
- **Alternative: Better Stack** (formerly Logtail)
  - Free tier available
  - Advanced uptime monitoring features

### ✅ USER ANALYTICS (Optional)

- **PostHog** (self-hosted, free)
  - User behavior tracking
  - A/B testing capabilities
  - Privacy-focused analytics

## Setup Instructions

### 1. Sentry Configuration

#### Frontend (Already Configured)

```bash
# .env.local
VITE_SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

#### Backend

```bash

# backend/.env
SENTRY_DSN=<https://your-sentry-dsn@sentry.io/project-id>
ENVIRONMENT=production
```

### 2. PostHog Analytics (Optional)

#### Frontend

```bash
# Install dependency (already added)
npm install

# Configure environment
# .env.local
VITE_POSTHOG_API_KEY=your-posthog-api-key
VITE_POSTHOG_HOST=https://app.posthog.com  # or your self-hosted URL
```

#### Backend (Optional)

```bash

# backend/.env
POSTHOG_API_KEY=your-posthog-api-key
POSTHOG_HOST=<https://app.posthog.com>
```

### 3. Uptime Monitoring

#### UptimeRobot Setup

1. Sign up at [uptimerobot.com](https://uptimerobot.com)
2. Add monitors for:
   - Frontend: `<https://goblin-assistant.vercel.app`>
   - API: `<https://goblin-assistant-backend.onrender.com/health`>
   - Brain: `<https://goblin-assistant-backend.onrender.com/health`>
3. Configure alert channels (email/SMS)

#### Alternative: Better Stack

1. Sign up at [betterstack.com](https://betterstack.com)
2. Set up uptime monitors for critical endpoints
3. Configure alerting rules

## Environment Variables

### Frontend (.env.local)

```bash
# Monitoring
VITE_SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
VITE_POSTHOG_API_KEY=your-posthog-api-key  # optional
VITE_POSTHOG_HOST=https://app.posthog.com  # optional
```

### Backend (.env)

```bash

# Monitoring
SENTRY_DSN=<https://your-sentry-dsn@sentry.io/project-id>
ENVIRONMENT=production

# Optional
POSTHOG_API_KEY=your-posthog-api-key
POSTHOG_HOST=<https://app.posthog.com>
```

## Cost Breakdown

| Service         | Cost               | Purpose                      |
| --------------- | ------------------ | ---------------------------- |
| **Sentry**      | $26/month          | Error tracking & performance |
| **Fly.io**      | Free               | Application metrics & logs   |
| **Vercel**      | Free               | Frontend analytics & logs    |
| **UptimeRobot** | Free               | Uptime monitoring            |
| **PostHog**     | Free (self-hosted) | User analytics               |

**Total Monthly Cost: $26** (vs $100+ with excessive monitoring)

## When to Add Back Complex Monitoring

### Datadog ($31/month)

- When daily active users > 100k
- Need advanced alerting and dashboards
- Require custom metrics and tracing

### Prometheus + Grafana

- When you need custom dashboards
- Complex alerting rules required
- Multi-service architecture with many components

### Current Stack is Sufficient For:

- ✅ < 100k daily active users
- ✅ Simple alerting needs
- ✅ Cost-conscious startups
- ✅ Fast-moving development
- ✅ Most production applications

## Troubleshooting

### Sentry Not Capturing Errors

```bash
# Check environment variables
echo $SENTRY_DSN
echo $VITE_SENTRY_DSN

# Verify initialization
# Frontend: Check browser console for Sentry logs
# Backend: Check application logs for "Sentry initialized"
```

### PostHog Not Tracking

```bash

# Check environment variables
echo $VITE_POSTHOG_API_KEY

# Verify initialization in browser dev tools

# posthog object should be available on window
```

### Logs Not Appearing

```bash
# Fly.io logs
fly logs

# Vercel logs
vercel logs

# Check log levels
# Backend: LOG_LEVEL=DEBUG for verbose logging
```

## Migration from Complex Monitoring

If you're migrating from Datadog/Prometheus:

1. **Keep Sentry** - Already configured
2. **Remove old dependencies** - Already done
3. **Update alerting** - Use UptimeRobot for uptime alerts
4. **Update dashboards** - Use Fly.io/Vercel built-in metrics
5. **Update documentation** - Point to this simplified setup

The simplified stack provides 80% of monitoring value at 20% of the cost and complexity.
