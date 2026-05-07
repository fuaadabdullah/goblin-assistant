Deployment scripts — usage & safety
=================================

This file documents the helper scripts added to `scripts/` for onboarding CI/CD secrets and deployment credentials.

Scripts
-------

- `setup-deployment-credentials.sh`
  - Interactive script that populates `terraform/terraform.tfvars` from the example.
  - Prompts for Render/GitHub/Supabase credentials and generates a JWT secret if needed.
  - Usage:

```bash
./scripts/setup-deployment-credentials.sh
```

- `setup-github-secrets.sh`
  - Uses the GitHub CLI (`gh`) to create repository secrets: `RENDER_API_KEY`, `RENDER_SERVICE_ID_STAGING`, `RENDER_SERVICE_ID_PROD`, `GITHUB_TOKEN`.
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
  - Orchestrator that runs the above helpers in sequence (interactive prompts).
  - Usage:

```bash
./scripts/run-full-deployment-setup.sh <owner> <repo> [vcs]
```

Security & notes
----------------

- Do NOT commit real secrets into the repository. `terraform/terraform.tfvars` is created locally by the credential script — review before committing.
- Prefer adding sensitive values to GitHub Secrets and CircleCI environment variables instead of storing them in files.
- The scripts assume you have `gh` and/or `circleci` CLIs if you want full automation. They will provide manual UI steps if the CLIs are not present.

Recommended quick flow
----------------------

1. Run the interactive credentials helper and review `terraform/terraform.tfvars`.
2. Commit the file locally if you want it in the branch (avoid pushing if it contains secrets you don't want in VCS).
3. Use `./scripts/setup-github-secrets.sh <owner> <repo>` to push secrets to GitHub Actions (requires `gh`).
4. Enable CircleCI and use `./scripts/setup-circleci.sh gh <org> <repo>` to set env vars.

If you need a non-interactive flow or CI job to securely ingest secrets from a vault, open an issue or ask me to implement it.
