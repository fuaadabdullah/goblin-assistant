# CI/CD Pipeline

Render is the canonical backend deployment platform, Vercel owns the web
deployment, and the repository no longer maintains Terraform or Kubernetes
deployment assets.

## Active Deployment Authority

| Surface | Authority |
|---|---|
| Backend production/staging blueprint | `render.yaml` |
| Web deployment config | `apps/web/vercel.json` |
| Fast validation | GitHub Actions |
| Longer build/test workflows | CircleCI, where enabled |
| Local container smoke | `docker-compose.yml` |
| Archived Fly reference | `fly.toml`, explicitly marked archived |

## GitHub Actions

| Workflow | Purpose |
|---|---|
| `.github/workflows/ci.yml` | Lint, type, test, build, contract, and policy checks. |
| `.github/workflows/deploy-staging.yml` | Builds the image and triggers a Render staging deploy. |
| `.github/workflows/deploy-prod.yml` | Manual production deploy through Render with an environment approval gate. |

The old Terraform plan workflow has been removed. Do not reintroduce a
Terraform workflow unless Terraform configuration is restored as a first-class
owned deployment surface with an ADR and matching validation.

## Required Secrets

### GitHub Actions

| Secret | Use |
|---|---|
| `RENDER_API_KEY` | Authenticate Render deployment API calls. |
| `RENDER_SERVICE_ID_STAGING` | Trigger staging backend deploys. |
| `RENDER_SERVICE_ID_PROD` | Trigger production backend deploys. |
| `GH_TOKEN` | Optional explicit GitHub token for helper scripts. |

### CircleCI

| Secret | Use |
|---|---|
| `RENDER_API_KEY` | Render deployment/API access where CircleCI owns a deploy step. |
| `DOCKER_LOGIN` | Container registry authentication. |
| `DOCKER_PASSWORD` | Container registry authentication. |
| `GITHUB_USER` | GitHub/package registry access. |
| `GITHUB_TOKEN` | GitHub/package registry access. |
| `SNYK_TOKEN` | Optional security scan integration. |

## Setup

1. Add the required GitHub Actions secrets in repository settings.
2. Add the required CircleCI environment variables if CircleCI is enabled.
3. Confirm Render has the production and staging services connected to the
   repository or accepts deploy triggers through the Render API.
4. Confirm Vercel has the web project connected and environment variables set.
5. Run the repo wiring check:

```bash
./scripts/verify-cicd-setup.sh
```

## Staging Deploy

Staging is triggered through `.github/workflows/deploy-staging.yml`.

Expected flow:

```text
tests -> Docker image build -> Render staging deploy trigger -> health check -> smoke tests
```

Health check:

```bash
curl -f https://goblin-assistant-staging.onrender.com/api/v1/health
```

## Production Deploy

Production deploys are manual and require the GitHub `production` environment
approval gate.

Expected flow:

```text
manual trigger -> pre-deploy secret checks -> approval -> Render production deploy trigger -> health check
```

Health check:

```bash
curl -f https://goblin-backend-dt30.onrender.com/api/v1/health
```

## Retired Paths

The following deployment assets were removed or archived to avoid split
ownership:

| Path | Status |
|---|---|
| `terraform/` | Removed. |
| `terraform.tfvars.example` | Removed. |
| `.github/workflows/terraform-plan.yml` | Removed. |
| `k8s/` | Removed. |
| `kind-config.yaml` | Removed. |
| `docker-compose.redis.yml` | Removed; use the canonical compose file. |
| `fly.toml` | Kept only as an explicitly archived reference. |

Do not create local secret files as a replacement for these retired paths.
Secrets belong in GitHub Actions, CircleCI, Render, Vercel, or the approved
secret backend.

## Troubleshooting

| Symptom | Check |
|---|---|
| Render deploy trigger fails | Verify `RENDER_API_KEY` and the correct service ID secret. |
| Health check fails after deploy | Check Render service logs, environment variables, and `/api/v1/health`. |
| Workflow cannot access container registry | Verify GitHub package permissions and Docker credentials. |
| Vercel web deploy is stale | Check Vercel project connection, build logs, and environment variables. |
| CI/CD verifier fails on retired paths | Ensure Terraform/Kubernetes files were not recreated and docs do not point contributors back to them. |
