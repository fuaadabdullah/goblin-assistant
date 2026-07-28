# Deployment Rollback Runbook

Use this runbook when a deploy to `main` has shipped a regression and
production needs to go back to a known-good state. See
`DEPLOYMENT_ARCHITECTURE.md` for the canonical two-platform model
(Render backend, Vercel frontend) this runbook assumes.

## 1. Confirm It's a Deploy, Not a Config/Data Issue

1. Check `GET /api/v1/health` (backend) and the Vercel deployment status
   page before assuming the *code* regressed — a bad env var change or a
   downstream provider outage looks identical to a bad deploy at first
   glance.
2. Identify which platform(s) actually shipped the regression:
   - Backend-only: `apps/api/**`, `Dockerfile`, `render.yaml` changed.
   - Frontend-only: `apps/web/**` changed.
   - Both, if the same commit touched both — check the commit range.

## 2. Roll Back the Backend (Render)

Render deploys are triggered by CircleCI's `deploy-render` job
(`.circleci/config.yml`), which POSTs to the Render Deploys API with
`clearCache: do_not_clear` — there is no separate "rollback" API call.

1. In the Render dashboard, open the `goblin-backend` service's Deploys
   tab and find the last deploy that was known-good.
2. Use Render's "Redeploy" action on that prior deploy, or revert the bad
   commit(s) on `main` and let CI redeploy normally — prefer the latter
   for anything beyond a same-day hotfix, since a dashboard-triggered
   redeploy diverges from what git history says is on `main`.
3. Watch CircleCI's `smoke-test` job (runs after `deploy-render`) —
   it polls `/health` and is the fastest signal the rollback actually
   took effect.
4. `DATABASE_URL`/`REDIS_URL` are wired via Render's `fromDatabase`/
   `fromService` references in `render.yaml`, not hardcoded — a rollback
   does not need separate credential handling unless the regression was a
   migration (see §4).

## 3. Roll Back the Frontend (Vercel)

1. In the Vercel dashboard, find the last production deployment before
   the regression and use "Promote to Production" — this is the fastest
   path and doesn't require a new build.
2. If reverting via git instead (to keep `main` and the deployed state in
   sync): revert the bad commit(s), push to `main`, and let CircleCI's
   `deploy-vercel` job run normally.
3. Frontend rollback is independent of the backend — you can roll back
   Vercel without touching Render and vice versa, since the frontend
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
  rollback target; Render is canonical (see
  `docs/operations/DEPLOYMENT_ARCHITECTURE.md` and enforced by
  `scripts/architecture/check_operational_policy.py`).
- There is no automated rollback trigger today — every path above is a
  manual dashboard action or a git revert + normal CI redeploy.
