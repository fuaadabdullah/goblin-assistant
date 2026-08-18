# Production Deployment Checklist

> Deprecated Kubernetes-era checklist. This path is retained for compatibility
> with the runbook migration map, but the old manifest-based deployment flow was
> removed from the repository.

Use the current deployment authority instead:

- Backend: `render.yaml`
- Web: `apps/web/vercel.json`
- CI/CD runbook: `docs/operations/CI_CD_PIPELINE_README.md`
- Deployment architecture: `docs/operations/DEPLOYMENT_ARCHITECTURE.md`
- Infra deployment notes: `docs/infra/deployment.md`

Minimum current checklist:

1. Confirm required Render, Vercel, GitHub Actions, and CircleCI secrets.
2. Run `./scripts/verify-cicd-setup.sh`.
3. Run the relevant contract, quality, and focused test gates for the release.
4. Trigger staging deploy and verify `/api/v1/health`.
5. Trigger production deploy through the GitHub `production` environment gate.
6. Verify production `/api/v1/health` and release-specific smoke endpoints.
