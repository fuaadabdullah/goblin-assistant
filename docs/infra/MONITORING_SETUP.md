# Monitoring Setup

The current monitoring guidance is intentionally lightweight and tied to the
active deployment model.

## Active Sources

| Signal | Source |
|---|---|
| Backend health | Render service health and `/api/v1/health` |
| Backend logs | Render service logs |
| Frontend logs/builds | Vercel project logs |
| Frontend analytics | Vercel Analytics, if enabled |
| Exceptions/traces | Sentry, if `SENTRY_DSN` is configured |
| Local container health | `docker-compose.yml` and API health endpoints |

## Minimum Production Checks

```bash
curl -f https://goblin-backend-dt30.onrender.com/api/v1/health
curl -f https://goblin-assistant.vercel.app
```

For API feature releases, add endpoint-specific smoke checks and inspect Render
logs for startup, import, database, and provider configuration errors.

## Retired Monitoring Assumptions

Fly.io built-in metrics and Kubernetes cluster observability are not active
production dependencies for this repository. Historical references should stay
in archive-only documents, not current operations instructions.
