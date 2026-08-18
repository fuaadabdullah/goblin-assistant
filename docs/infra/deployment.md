# Deployment

Goblin Assistant uses a two-platform deployment model:

| Surface | Platform | Canonical File |
|---|---|---|
| Backend API | Render | `render.yaml` |
| Frontend web app | Vercel | `apps/web/vercel.json` |

## Backend

Render reads `render.yaml` for the backend service, Redis-compatible key-value
service, and Postgres database. The backend health check path is
`/api/v1/health`.

Production URL:

```bash
https://goblin-backend-dt30.onrender.com
```

Verify production:

```bash
curl -f https://goblin-backend-dt30.onrender.com/api/v1/health
```

Verify staging:

```bash
curl -f https://goblin-assistant-staging.onrender.com/api/v1/health
```

## Frontend

Vercel owns the web deployment. Keep web environment variables aligned with the
Render backend URL and the Supabase project used by the API.

## Local Containers

Use the root `docker-compose.yml` for local container smoke and sandbox worker
coordination. The old Redis-only compose file was removed; Redis should be
modeled through the canonical compose stack or managed services.

## Retired Platforms

Terraform, Kubernetes manifests, kind config, Netlify deployment docs, GCP chat
deployment docs, and active Fly.io deployment flows were retired. Do not add
new deployment instructions for those platforms unless they are reintroduced as
owned, tested targets with an ADR and CI validation.
