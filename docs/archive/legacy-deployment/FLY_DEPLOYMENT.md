# 🚀 Deploying Goblin Assistant to Fly.io

## Quick Start (5 minutes)

### Option 1: Fly.io Dashboard / CLI (recommended)

1. Push your code to GitHub (if not already done):

   ```bash
   cd /Users/fuaadabdullah/ForgeMonorepo
   git add .
   git commit -m "Ready for Fly.io deployment"
   git push origin main
   ```

2. Ensure `flyctl` is installed and you're logged in:

   ```bash

   curl -L <https://fly.io/install.sh> | sh
   fly auth login
   ```

3. Create or link an app (one-time):

   ```bash
   cd apps/goblin-assistant
   fly launch --name goblin-assistant --region iad --no-deploy
   ```

   - `--no-deploy` prevents an immediate deploy during initial setup so you can set secrets first.

4. Set Environment Variables/Secrets

   ```bash

   fly secrets set ANTHROPIC_API_KEY=sk-... OPENAI_API_KEY=sk-... \
     DATABASE_URL=postgres://user:pass@host:5432/dbname JWT_SECRET_KEY=secret
   ```

5. Deploy the app:

   ```bash
   fly deploy --remote-only --yes
   ```

6. Verify the deployment

   ```bash

   # Health check
   curl <https://goblin-assistant.fly.dev/health>
   ```

---

## What Gets Deployed

The `fly.toml` configuration defines how Fly builds and runs the app:

- Buildpacks (or Docker) for Python FastAPI
- Process: uvicorn backend.main:app --host 0.0.0.0 --port 8000
- Ports: 80/443 with TLS
- Health check: `/health`

Fly apps are automatically served under `<https://<app>.fly.dev`> (unless you attach a custom domain).

---

## Environment Variables

### Required

- `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, `GEMINI_API_KEY`, `GROK_API_KEY` (provider-specific)
- `DATABASE_URL` (Postgres, Superbase, or managed DB)
- `JWT_SECRET_KEY` (auth token secret)

### Optional

- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` (OAuth)
- `SENTRY_DSN` (Sentry for error tracking)
- `POSTHOG_API_KEY` (analytics)

Use `fly secrets set KEY=value` to add secrets and `fly secrets list` to confirm.

---

## Deploying Using CI/CD (example)

If using CircleCI or GitHub Actions, use `flyctl` to login and deploy. Example pipeline steps:

- Install Fly CLI
- Authorize with `FLY_TOKEN`
- `fly deploy --remote-only --yes`

The repo already includes `.circleci/config.yml` with Fly deployment steps.

---

## Custom Domains & TLS

1. Add the domain in Fly dashboard or use `flyctl dns attach` to attach a custom domain.
2. Update DNS records as instructed by Fly.
3. Set the Cloudflare origin or proxy if you use Cloudflare in front of Fly.

---

## After Deployment

1. Get your backend URL: `<https://goblin-assistant.fly.dev`>
2. Test health endpoint

   ```bash
   curl https://goblin-assistant.fly.dev/health
   ```

3. Update frontend environment variable

   ```bash

   VITE_FASTAPI_URL=<https://goblin-assistant.fly.dev>
   ```

---

## Troubleshooting

### Build Failed

- Check `fly.toml` and `requirements.txt`.
- Inspect `flyctl deploy` logs and `fly status`.

### Runtime Errors

- Verify secrets were set correctly: `fly secrets list`.
- Check `DATABASE_URL` and DB connectivity.

---

## Costs & Scaling

- Fly has both free and paid tiers depending on resources and regions. See <https://fly.io> for details.
- For production, set resource limits in `fly.toml` and scale horizontally/vertically using the Fly dashboard or `flyctl scale`.

---

## Updating Fly app config

- To change any runtime settings, edit `fly.toml` then run `fly deploy`.

---

**Last Updated**: December 3, 2025
**Status**: Ready for Fly.io production deployments
