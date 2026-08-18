# Attestation Webhook Deployment

> Deprecated Kubernetes-era runbook. This path is retained for compatibility
> with the runbook migration map, but the manifest-based admission webhook
> deployment assets were removed from the repository.

The current repository does not own an active Kubernetes deployment target.
Keep webhook implementation and tests in the API codebase, but do not use this
document as deployment guidance.

Current operational references:

- `docs/operations/DEPLOYMENT_ARCHITECTURE.md`
- `docs/operations/CI_CD_PIPELINE_README.md`
- `docs/infra/deployment.md`
- `render.yaml`

If Kubernetes attestation becomes an owned target again, reintroduce it through
an ADR, source-controlled manifests, security review, and CI validation.
