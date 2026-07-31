# Decision: Sandbox & Celery Feature Gate Strategy

**Date:** 2026-07-31
**Status:** Decided

## Context

The sandbox (secure code execution) and Celery (background task workers)
features require Docker-in-Docker infrastructure that is not configured
locally or on Render. The question is whether to:

1. Gate them behind a feature flag and disable by default, or
2. Add `docker-compose.goblinos-override.yml` to the local stack

## Decision

**Gate behind feature flags and disable by default.** Do not add Celery
workers or priority queues to the default local or Render deployment.

## Rationale

- **AGENTS.md rule:** "Don't add Celery workers or priority queues. Three
  worker pools at solo-dev scale is infrastructure cosplay."
- The sandbox requires Docker-in-Docker (a sandbox worker that spawns
  containers), which adds complexity and security surface area.
- Neither feature is needed for dogfooding the core chat experience.
- The existing docker-compose profiles (`--profile sandbox`, `--profile
  workers`) already make these features opt-in.

## Current State (already implemented)

### Sandbox

- `SANDBOX_ENABLED=false` is the default in `.env.example`
- `sandbox_config.py` reads `SANDBOX_ENABLED` and gates execution
- `sandbox_api.py` checks `SANDBOX_ENABLED` at every endpoint and returns
  an error when disabled (lines 97, 353, 421, 455)
- Docker Compose: sandbox worker behind `--profile sandbox` profile
- Docker Compose: MinIO (sandbox storage) behind `--profile sandbox` profile

### Celery

- Docker Compose: Celery workers behind `--profile workers` profile
- Docker Compose: Celery beat behind `--profile workers` profile
- Docker Compose: Flower (task monitor) behind `--profile workers` profile
- Celery is not started by default; requires explicit opt-in

## How to Enable (if needed)

### Sandbox

```bash
# 1. Set the feature flag
export SANDBOX_ENABLED=true

# 2. Build the sandbox image
docker compose --profile build build sandbox-builder

# 3. Start with sandbox profile
docker compose --profile sandbox up -d
```

### Celery

```bash
# Start with workers profile
docker compose --profile workers up -d
```

## What NOT to Do

- Do not add `docker-compose.goblinos-override.yml` to the default stack.
  That file is for external USB drive storage (Redis data), not for
  sandbox/celery features.
- Do not add Celery worker pools or priority queues. The existing three
  pools (high, default, low) are sufficient for the current scale.
- Do not enable sandbox in production (Render) without a security review.

## Revisit When

- The user base grows beyond solo-dev scale and background task queuing
  becomes a bottleneck.
- A concrete need for secure code execution arises (e.g., user-submitted
  code, plugin system).
- Docker-in-Docker infrastructure is properly provisioned with network
  isolation and resource limits.