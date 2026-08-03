# Render Secrets — Required Environment Keys

Status: canonical. This is the authoritative list of environment keys that must
be set for the Render `goblin-backend` service. Values are **never committed**.
The blueprint (`render.yaml`) creates and links the
`goblin-shared-secrets` environment group; Render requires its secret keys and
values to be managed in the dashboard.

## Where keys are managed

1. Open the Render dashboard → **Environment Groups** → `goblin-shared-secrets`.
2. Add or edit the keys below. They are intentionally omitted from the
   Blueprint because Render does not support `sync: false` inside environment
   groups; dashboard-added variables survive later Blueprint syncs.
3. After changing values, trigger **Manual Deploy → Deploy latest commit** (or
   push to `main`, which auto-deploys — see "Auto-deploy" below).

`DATABASE_URL` and `REDIS_URL` are **not** in this list: they are wired
automatically from the `goblin-postgres` database and `goblin-redis` keyvalue
service via `fromDatabase` / `fromService` bindings in `render.yaml`.

## Required for dogfooding

| Key | Purpose |
| --- | --- |
| `JWT_SECRET_KEY` | FastAPI/JWT signing secret read directly by the auth runtime. |
| `SUPABASE_URL` | Supabase project URL — required to validate sessions forwarded by the web app. |
| `SUPABASE_ANON_KEY` | Supabase anon key. |
| One of `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` | Dogfooding LLM provider. At least one must pass `/api/v1/health/providers`. |

## Strongly recommended

| Key | Purpose |
| --- | --- |
| `SENTRY_DSN` | Error tracking. Without it, Sentry is disabled and startup logs a warning. |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase administrative/data integration. Not required merely to validate user sessions. |

## Optional provider keys

Each key activates the matching provider in `config/providers.toml` when
present. Leave unset to keep the provider unconfigured (it shows as `unknown`
in `/api/v1/health/providers` and is skipped by routing).

| Key(s) | Provider | Notes |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | Anthropic | May be the primary dogfooding provider instead of OpenAI. |
| `GOOGLE_AI_API_KEY` | Google Gemini | |
| `DEEPSEEK_API_KEY` | DeepSeek | |
| `GROQ_API_KEY` | Groq | |
| `SILICONEFLOW_API_KEY` | SiliconeFlow | |
| `TOGETHER_API_KEY` | Together AI | |
| `HUGGINGFACE_API_KEY` | Hugging Face | |
| `COHERE_API_KEY` | Cohere | |
| `AZURE_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_REGION`, `AZURE_DEPLOYMENT_ID` | Azure OpenAI | All four must be set together; the provider stays unconfigured until every companion key exists. |
| `DASHSCOPE_API_KEY`, `DASHSCOPE_ENDPOINT` | Aliyun DashScope | Both required together. |
| `ATLASSIAN_API_TOKEN` | Rovo Dev (Goblin Coder) | Internal code agent only; not user-facing. |
| `LOCAL_LLM_API_KEY` | Local LLM test hook | Only needed for local/test LLM endpoints. |

## Keys that must NOT be set on Render

These are stale or belong to decommissioned infrastructure (GCP VMs terminated
2026-01-11). Setting them reactivates dead providers and confuses routing:

- `OLLAMA_GCP_URL`, `LLAMACPP_GCP_URL` — GCP inference VMs removed.
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` — was for self-hosted MinIO.
- `GOOGLE_CLOUD_VLLM_ENDPOINT`, `GOOGLE_CLOUD_VLLM_API_KEY` — vLLM cluster
  inactive until GCP infra is redeployed.
- `VERTEX_AI_PROJECT`, `VERTEX_AI_LOCATION`, `GOOGLE_APPLICATION_CREDENTIALS` —
  only for the inactive `gcp_vm` / `router_models` LiteLLM backends.

## Verifying keys after setting them

```bash
# Liveness of the app itself:
curl https://goblin-backend-dt30.onrender.com/api/v1/health

# Live provider connectivity probe (re-checks every configured provider):
curl https://goblin-backend-dt30.onrender.com/api/v1/health/providers
```

`/api/v1/health/providers` returns `status: healthy` when every configured
provider passes a live probe, `warnings` when at least one is healthy but
others fail, and `degraded` when nothing healthy remains. Providers with no
key set report `configured: false` and do not count against the summary.

## Auto-deploy

- **Render**: `render.yaml` sets `branch: main` and
  `autoDeployTrigger: checksPass`, so pushes to `main` redeploy
  `goblin-backend` after linked CI checks pass (requires the GitHub repo to be
  connected in the Render dashboard).
- **Vercel**: the `goblin-assistant` web project auto-deploys `main` by
  default; `apps/web/vercel.json` pins this with
  `git.deploymentEnabled.main = true`.
