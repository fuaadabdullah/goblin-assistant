---
title: "DEPLOYMENT ARCHITECTURE"
description: "Canonical deployment architecture and targets"
---

## Deployment Architecture

### Canonical targets (August 2026)

Goblin Assistant uses a Vercel + Oracle deployment model:

- Frontend: **Vercel**
- Backend/runtime: **Oracle Cloud Infrastructure (OCI) Always Free**, via `infra/oracle/`
- Runtime topology: **FastAPI + Redis + Celery** share the same OCI VM initially
- Data/auth layer: **Supabase** (auth, PostgreSQL, pgvector)
- External APIs: OpenAI / Groq / Anthropic / etc.

Canonical backend runtime on the OCI VM:

- `cd infra/oracle && docker compose pull && docker compose up -d --no-build --remove-orphans`
- The API container itself runs `uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 2`
  inside that stack.
- Redis runs in the same compose project and backs both app caching and Celery.
- Celery starts with `--concurrency=1`; raise to 2 only after measuring CPU and
  memory headroom on the A1 VM.

Recommended OCI persistent-storage layout:

- Keep application source under Git/CI, not on the persistent volume.
- Mount the block volume at a durable host path for mutable state such as
  `/opt/goblin/data`, `/var/lib/docker`, `/var/lib/redis`, `/var/log/goblin`,
  and `/backups`.
- Use `infra/oracle/scripts/setup-persistent-storage.sh` to format the data
  volume, mount it at `/opt/goblin/data`, and bind the Docker, Redis, log, and
  backup paths into that durable filesystem.
- Assign an OCI volume backup policy to the durable block volume so the
  persistent Docker, Redis, log, and backup state is protected by scheduled
  backups rather than ad hoc tarballs.
- Size the boot volume for the OS and immutable runtime needs; reserve the
  attached volume for data that must survive container replacement.

### OCI lifecycle monitor

Use a dedicated OCI lifecycle monitor to track:

- VM reachable
- API reachable
- disk utilization
- memory utilization
- container health
- last deployment
- public IP
- SSL expiration

Recommended entrypoint: `scripts/ops/oci_lifecycle_monitor.py`.

Treat Oracle Always Free as a dogfooding platform, not a production SLA. Oracle
documents that idle Always Free compute instances may be reclaimed after 7 days
when CPU, network, and, for A1 shapes, memory utilization remain below the idle
thresholds.

### Source of truth files

- Oracle VM provisioning: `infra/oracle/terraform/main.tf`
- Oracle VM bootstrap: `infra/oracle/terraform/cloud-init.yml`
- Oracle VM storage bootstrap: `infra/oracle/scripts/setup-persistent-storage.sh`
- Oracle runtime stack: `infra/oracle/docker-compose.yml`
- Oracle reverse proxy/TLS: `infra/oracle/Caddyfile`
- Redis runtime config: `redis.conf`
- OCI lifecycle monitor: `scripts/ops/oci_lifecycle_monitor.py`
- Frontend deployment config: `vercel.json`
- Production deploy workflow: `.github/workflows/deploy-prod.yml`
- Archived Render reference: `render.yaml`
- Archived Fly reference: `fly.toml`
- Primary backend container definition: `Dockerfile`

### Governance

- `make check-operational-policy` verifies that `infra/oracle/` remains the
  canonical backend target, `render.yaml` and `fly.toml` stay explicitly
  archived, Docker runtime images do not fall back to broad repository copies
  or root users, and dependency update automation remains configured.

### Archived/deprecated targets

The following are no longer canonical for production in this repository:

- Render deployment config (`render.yaml`)
- Fly.io deployment configs/scripts
- GCP chat deployment wrappers
- Kamatera-specific deployment wrappers
- Duplicate backend entrypoint files

### Operational checklist

1. Configure the Oracle VM, DNS A record, and backend secrets.
2. Deploy the backend from `infra/oracle/` and verify `GET /api/v1/health`.
3. Point Vercel environment variables at the Oracle backend URL.
4. Deploy frontend on Vercel.
5. Validate end-to-end auth/chat/routing flows.
6. Confirm the OCI lifecycle monitor is green before treating the VM as stable.

### Notes

- Keep deployment docs aligned with these canonical files.
- Keep Supabase PostgreSQL + pgvector as the durable data plane; do not add a
  second PostgreSQL deployment or Chroma sidecar to the production path.
- Back up anything irreplaceable externally; do not treat the Oracle VM as the
  sole copy of long-lived data.
- Do not reintroduce platform-specific wrappers unless they become an explicitly supported target.
