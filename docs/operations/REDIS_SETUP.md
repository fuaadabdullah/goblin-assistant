# Redis Setup

Redis-compatible storage is used for caching, rate limiting, session-adjacent
state, task result caching, provider health, and distributed locks.

## Production

Production Redis is provisioned through the canonical Render blueprint:

```yaml
# render.yaml
- type: keyvalue
  name: goblin-redis
```

The API receives `REDIS_URL` from Render:

```yaml
- key: REDIS_URL
  fromService:
    type: keyvalue
    name: goblin-redis
    property: connectionString
```

Do not create or commit `docker-compose.redis.yml`; the Redis-only compose file
was removed. Use Render-managed key-value storage in hosted environments and
the canonical root compose stack for local container smoke.

## Local Development

Use the root `docker-compose.yml` when a local Redis-compatible service is
needed alongside the API stack.

Typical local environment shape:

```bash
REDIS_URL=redis://localhost:6379/0
```

Keep local passwords and connection strings in untracked environment files or
the approved secret backend.

## Verification

```bash
./scripts/verify-cicd-setup.sh
curl -f http://127.0.0.1:8001/api/v1/health
```

For hosted environments, verify the Render service health check path:

```bash
curl -f https://goblin-backend-dt30.onrender.com/api/v1/health
```
