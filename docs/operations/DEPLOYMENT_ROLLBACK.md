# Deployment Rollback Runbook

Use this runbook when a deploy to `main` has shipped a regression and
production needs to go back to a known-good state. See
`DEPLOYMENT_ARCHITECTURE.md` for the canonical Vercel frontend + OCI backend
model this runbook assumes.

## 1. Confirm It's a Deploy, Not a Config/Data Issue

1. Check `GET /api/v1/health` (backend) and the Vercel deployment status
   page before assuming the *code* regressed — a bad env var change or a
   downstream provider outage looks identical to a bad deploy at first
   glance.
2. Identify which platform(s) actually shipped the regression:
   - Backend-only: `apps/api/**`, `Dockerfile`, `infra/oracle/**`,
     `render.yaml` (archived), or `fly.toml` (archived) changed.
   - Frontend-only: `apps/web/**` changed.
   - Both, if the same commit touched both — check the commit range.

## 2. Roll Back the Backend (OCI)

OCI deployments are triggered by the `deploy-prod.yml` workflow, which SSHes
into the Oracle VM, pulls `main`, and runs the compose stack from
`infra/oracle/`.

1. Revert the bad commit(s) on `main`, or use `git revert` to create a
   corrective commit if the bad change already shipped.
2. SSH into the Oracle VM and redeploy the reverted branch state:

```bash
ssh ubuntu@<oracle-vm> "cd ~/goblin-assistant && git pull origin main && cd infra/oracle && docker compose pull && docker compose up -d --no-build --remove-orphans"
```

3. Watch `GET /api/v1/health` on the Oracle backend URL and confirm the
   reverted build is live.
4. `DATABASE_URL` stays external via Supabase, while `REDIS_URL` is local to
   the OCI compose stack, so a code rollback usually does not need separate
   credential handling unless the regression was a schema migration or Redis
   state issue (see §4).

## 3. Roll Back the Frontend (Vercel)

1. In the Vercel dashboard, find the last production deployment before
   the regression and use "Promote to Production" — this is the fastest
   path and doesn't require a new build.
2. If reverting via git instead (to keep `main` and the deployed state in
   sync): revert the bad commit(s), push to `main`, and let CircleCI's
   `deploy-vercel` job run normally.
3. Frontend rollback is independent of the backend — you can roll back
   Vercel without touching OCI and vice versa, since the frontend
   talks to the backend over the stable `/api/v1` contract
   (see ADR-0002).

## 4. If a Database Migration Shipped

1. Check `apps/api/alembic/versions/` for any migration in the bad
   deploy's commit range.
2. Rolling back application code does **not** roll back the schema —
   confirm whether the previous code version is actually compatible with
   the new schema before redeploying it. If not, you need
   `alembic downgrade` before the code rollback will work correctly.
3. Treat this case as higher-risk than a pure code rollback — coordinate
   before running `alembic downgrade` against production data.

## 5. Post-Rollback

1. Confirm smoke tests / manual golden-path checks pass on both
   platforms.
2. File the regression (root cause, affected commit range, detection
   time) so the next deploy doesn't reintroduce it.
3. If the rollback required a dashboard action that diverged from `main`
   (§2.2, §3.1), reconcile git history afterward so `main` matches what's
   actually deployed.

## Notes

- Fly.io (`fly.toml`) is explicitly archived — do not use it as a
  rollback target. Render (`render.yaml`) is also archived. OCI is the
  canonical backend target (see `docs/operations/DEPLOYMENT_ARCHITECTURE.md`
  and enforced by `scripts/architecture/check_operational_policy.py`).
- There is no automated rollback trigger today — every path above is a
  manual dashboard action or a git revert + normal CI redeploy.
