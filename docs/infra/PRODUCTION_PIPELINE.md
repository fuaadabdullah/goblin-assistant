# Production Pipeline

Render is the canonical backend production platform and Vercel is the canonical
frontend platform. The repository no longer maintains Fly.io, Terraform, or
Kubernetes production deployment flows.

## Flow

```text
merge to main -> CI and policy gates -> manual production workflow -> Render deploy trigger -> health check
```

## Source Files

| Concern | Source |
|---|---|
| Backend deploy blueprint | `render.yaml` |
| Production deploy workflow | `.github/workflows/deploy-prod.yml` |
| Staging deploy workflow | `.github/workflows/deploy-staging.yml` |
| Web deploy config | `apps/web/vercel.json` |
| Local container smoke | `docker-compose.yml` |

## Required Checks

Before a production deploy, keep the proof bundle explicit:

```bash
make check-operational-policy
make contract-checks
make check-quality-baseline
./scripts/verify-cicd-setup.sh
```

Add focused API/web/runtime checks for the changed surface. Do not use this doc
as a substitute for current command output.

## Deployment

Production deployment is manual through `.github/workflows/deploy-prod.yml`.
That workflow checks Render secrets, requires the GitHub `production`
environment approval gate, triggers a Render deploy, and verifies
`/api/v1/health`.

Staging deployment is handled by `.github/workflows/deploy-staging.yml`, which
builds the Docker image, triggers Render staging, and runs a health smoke.

## Retired Paths

The old Fly.io, Terraform, and Kubernetes production paths were removed to keep
deployment ownership simple. `fly.toml` remains only as an explicitly archived
reference required by the operational policy check.
