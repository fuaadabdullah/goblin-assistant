---
title: "DEPLOYMENT ARCHITECTURE"
description: "Canonical deployment architecture and targets"
---

## Deployment Architecture

### Canonical targets (March 2026)

Goblin Assistant uses a two-platform deployment model:

- Frontend: **Vercel**
- Backend: **Render**

Canonical backend runtime entrypoint:

- `uvicorn api.main:app --host 0.0.0.0 --port $PORT`

### Source of truth files

- Backend deployment blueprint: `render.yaml`
- Frontend deployment config: `vercel.json`
- Primary backend container definition: `Dockerfile`
- Deployment wrappers:
  - `deploy-render.sh`
  - `deploy-vercel.sh`
  - `deploy.sh` (`vercel|render|test`)

### Archived/deprecated targets

The following are no longer canonical for production in this repository:

- Fly.io deployment configs/scripts
- GCP chat deployment wrappers
- Kamatera-specific deployment wrappers
- Duplicate backend entrypoint files

### Operational checklist

1. Configure Render environment secrets for backend.
2. Deploy backend from `render.yaml` and verify `/health`.
3. Configure Vercel environment variables pointing to Render backend URL.
4. Deploy frontend on Vercel.
5. Validate end-to-end auth/chat/routing flows.

### Notes

- Keep deployment docs aligned with these canonical files.
- Do not reintroduce platform-specific wrappers unless they become an explicitly supported target.
