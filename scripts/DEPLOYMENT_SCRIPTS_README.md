Deployment scripts
==================

This directory keeps thin wrappers for supported deployment-adjacent setup.
Render is the canonical backend platform (`render.yaml`), Vercel owns the web
deployment (`apps/web/vercel.json`), and Fly/Terraform/Kubernetes deployment
paths are retired or archived.

Supported helpers
-----------------

- `setup-github-secrets.sh`
  - Uses the GitHub CLI (`gh`) to create repository secrets:
    `RENDER_API_KEY`, `RENDER_SERVICE_ID_STAGING`, `RENDER_SERVICE_ID_PROD`,
    and `GH_TOKEN`.
  - Requires `gh auth login` beforehand.
  - Usage:

```bash
./scripts/setup-github-secrets.sh <owner> <repo>
```

- `setup-circleci.sh`
  - Helps configure CircleCI environment variables.
  - Uses the `circleci` CLI when available; otherwise prints manual UI steps.
  - Usage:

```bash
./scripts/setup-circleci.sh gh <org> <repo>
```

- `verify-cicd-setup.sh`
  - Verifies the active repo wiring for GitHub Actions, CircleCI, Render,
    Vercel, Docker, and retired Terraform/Kubernetes paths.
  - Usage:

```bash
./scripts/verify-cicd-setup.sh
```

Security notes
--------------

- Do not commit real secrets into the repository.
- Prefer GitHub Secrets, CircleCI environment variables, Render environment
  variables, Vercel environment variables, or the approved secret backend for
  sensitive values.
- Do not recreate `terraform.tfvars`; Terraform deployment assets were removed
  from this repo.
