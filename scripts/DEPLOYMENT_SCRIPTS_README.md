Deployment scripts — usage & safety
=================================

This file documents the helper scripts added to `scripts/` for onboarding the hybrid GitHub Actions + CircleCI CI/CD flow.

Scripts
-------

- `setup-ci-cd.sh`
  - Primary entrypoint for the hybrid CI/CD setup. Installs dependencies, runs the core gates, and offers to set up CircleCI.
  - Usage:

```bash
./scripts/setup-ci-cd.sh
```

- `setup-deployment-credentials.sh`
  - Legacy compatibility helper for Terraform-enabled checkouts.
  - In this repository it prints the preferred hybrid setup path and exits successfully.
  - Usage:

```bash
./scripts/setup-deployment-credentials.sh
```

- `setup-github-secrets.sh`
  - Uses the GitHub CLI (`gh`) to create repository secrets: `RENDER_API_KEY`, `RENDER_SERVICE_ID_STAGING`, `RENDER_SERVICE_ID_PROD`, `GH_TOKEN`.
  - Requires `gh auth login` beforehand.
  - Usage:

```bash
./scripts/setup-github-secrets.sh <owner> <repo>
```

- `setup-circleci.sh`
  - Helper to set CircleCI environment variables. Uses `circleci` CLI when available; otherwise prints UI steps.
  - Usage:

```bash
./scripts/setup-circleci.sh gh <org> <repo>
```

- `run-full-deployment-setup.sh`
  - Orchestrator that runs the hybrid CI/CD setup and then optionally the GitHub secrets helper.
  - Usage:

```bash
./scripts/run-full-deployment-setup.sh <owner> <repo> [vcs]
```

Security & notes
----------------

- Do NOT commit real secrets into the repository.
- Prefer adding sensitive values to GitHub Secrets and CircleCI environment variables instead of storing them in files.
- The scripts assume you have `gh` and/or `circleci` CLIs if you want full automation. They will provide manual UI steps if the CLIs are not present.

Recommended quick flow
----------------------

1. Run `./scripts/setup-ci-cd.sh` to install dependencies, run the core gates, and optionally set up CircleCI.
2. Use `./scripts/setup-github-secrets.sh <owner> <repo>` to push secrets to GitHub Actions (requires `gh`).
3. Use `./scripts/setup-circleci.sh gh <org> <repo>` if you want to seed CircleCI environment variables separately.

If you need a non-interactive flow or CI job to securely ingest secrets from a vault, open an issue or ask me to implement it.
