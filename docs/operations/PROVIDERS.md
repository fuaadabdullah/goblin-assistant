# Provider Matrix (Canonical Operations Reference)

This document is the canonical operations reference for provider configuration mapping:

- **Provider**
- **Environment variables**
- **Default model**
- **Infrastructure tier**
- **Active / Visible / Selectable status**

## Sources of truth

- Provider config: `config/providers.toml`
- Runtime listing and selectability logic: `apps/api/src/api/providers/dispatcher.py`
- Environment examples:
  - `.env.example`
  - `apps/api/.env.example`

## Status semantics

- **Active**: value of `is_active` in `config/providers.toml`.
- **Visible**: provider ID is present in `visible_providers` and not `hidden`.
- **Selectable**:
  - Runtime inventory uses health-aware selectability (`check_provider` sets `is_selectable` based on health for configured providers).
  - Base configuration gate is `ProviderDispatcher.is_configured(provider_id)`:
    - `mock`: always configured.
    - `vertex_ai`: requires project + credentials (see rules table below).
    - `azure_openai`: requires API key + endpoint + deployment (deployment may come from `default_deployment` in TOML).
    - `selectable_requires_env = true`: requires `endpoint_env` to be set.
    - otherwise, if `api_key_env` exists: requires that API key env var.
    - otherwise, for self-hosted without key: requires endpoint env.
    - fallback: non-empty endpoint in config.

## Provider matrix

| Provider | Environment variables | Default model | Tier | Active | Visible | Selectable (configuration rule) |
| --- | --- | --- | --- | --- | --- | --- |
| `openai` | `OPENAI_API_KEY`, `OPENAI_ENDPOINT` | `gpt-4o-mini` | `cloud` | Yes | Yes | Requires `OPENAI_API_KEY` |
| `anthropic` | `ANTHROPIC_API_KEY`, `ANTHROPIC_ENDPOINT` | `claude-3-5-haiku-latest` | `cloud` | Yes | Yes | Requires `ANTHROPIC_API_KEY` |
| `groq` | `GROQ_API_KEY`, `GROQ_ENDPOINT` | `llama-3.1-8b-instant` | `cloud` | Yes | Yes | Requires `GROQ_API_KEY` |
| `together` | `TOGETHER_API_KEY`, `TOGETHER_ENDPOINT` | — (not set) | `cloud` | Yes | Yes | Requires `TOGETHER_API_KEY` |
| `siliconeflow` | `SILICONEFLOW_API_KEY`, `SILICONEFLOW_ENDPOINT` | `Qwen/Qwen2.5-7B-Instruct` | `cloud` | Yes | Yes | Requires `SILICONEFLOW_API_KEY` |
| `deepseek` | `DEEPSEEK_API_KEY`, `DEEPSEEK_ENDPOINT` | `deepseek-chat` | `cloud` | Yes | Yes | Requires `DEEPSEEK_API_KEY` |
| `gemini` | `GOOGLE_AI_API_KEY`, `GEMINI_ENDPOINT` | `gemini-2.0-flash` | `cloud` | Yes | Yes | Requires `GOOGLE_AI_API_KEY` |
| `azure_openai` | `AZURE_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_DEPLOYMENT_ID` (or TOML `default_deployment`), `AZURE_REGION` (listed in `requires_env`) | `gpt-4o-mini` | `private` | Yes | Yes | Requires API key + endpoint + deployment value |
| `vertex_ai` | `VERTEX_AI_PROJECT` (or `GCP_PROJECT_ID`), one of `GOOGLE_APPLICATION_CREDENTIALS` / `VERTEX_AI_SERVICE_ACCOUNT_JSON` / `GCP_SERVICE_ACCOUNT_KEY`, optional `VERTEX_AI_ENDPOINT` | `gemini-2.5-flash` | `private` | Yes | Yes | Requires project + credentials |
| `aliyun` | `DASHSCOPE_API_KEY`, `DASHSCOPE_ENDPOINT` | `qwen-plus` | `private` | Yes | Yes | Requires `DASHSCOPE_API_KEY` |
| `huggingface` | `HUGGINGFACE_API_KEY`, `HUGGINGFACE_ENDPOINT` | — (not set) | `cloud` | Yes | Yes | Requires `HUGGINGFACE_API_KEY` |
| `ollama_gcp` | `OLLAMA_GCP_ENDPOINT` | `qwen2.5:3b` | `self_hosted` | Yes | Yes | `selectable_requires_env=true` ⇒ requires `OLLAMA_GCP_ENDPOINT` |
| `llamacpp_gcp` | `LLAMACPP_GCP_ENDPOINT` | — (empty in TOML) | `self_hosted` | Yes | Yes | `selectable_requires_env=true` ⇒ requires `LLAMACPP_GCP_ENDPOINT` |
| `ollama_local` | `OLLAMA_LOCAL_ENDPOINT` | `qwen2.5:3b` | `self_hosted` | Yes | Yes | `selectable_requires_env=true` ⇒ requires `OLLAMA_LOCAL_ENDPOINT` |
| `colab_worker` | `COLAB_WORKER_ENDPOINT`, `COLAB_WORKER_API_KEY` | `gemma-3-12b` | `self_hosted` | Yes | Yes | Requires endpoint + API key (`is_configured` enforces both) |
| `replicate` | `REPLICATE_API_KEY`, `REPLICATE_ENDPOINT` | — (not set) | `cloud` | No | No | Requires `REPLICATE_API_KEY` |
| `cohere` | `COHERE_API_KEY`, `COHERE_ENDPOINT` | — (not set) | `cloud` | No | No | Requires `COHERE_API_KEY` |
| `mock` | `MOCK_PROVIDER_ENDPOINT` (optional for runtime testing) | `mock-gpt` | `mock` | Yes | No (`hidden=true`) | Always configured (`provider_id == "mock"`) |

## Selectability rules (runtime detail)

| Provider path | Rule summary |
| --- | --- |
| `vertex_ai` | Configured only if project is present (`VERTEX_AI_PROJECT` or `GCP_PROJECT_ID`) **and** credentials are present (`GOOGLE_APPLICATION_CREDENTIALS` or `VERTEX_AI_SERVICE_ACCOUNT_JSON` or `GCP_SERVICE_ACCOUNT_KEY`). |
| `azure_openai` | Configured only if API key + endpoint + deployment are available. Deployment may come from `AZURE_DEPLOYMENT_ID` or TOML `default_deployment` / `default_model`. |
| `selectable_requires_env=true` | Configured only when `endpoint_env` is set in environment. |
| Providers with `api_key_env` | Configured only when API key env var is set. |
| Health gate (`check_provider`) | Even when configured, `is_selectable` can still be false if health check fails. |

## Environment reference cross-check

### Present in `.env.example`

- Keys/endpoints for most configured providers are documented, including:
  `OPENAI_*`, `ANTHROPIC_*`, `GROQ_*`, `SILICONEFLOW_*`, `DEEPSEEK_*`,
  `TOGETHER_ENDPOINT`, `REPLICATE_ENDPOINT`, `HUGGINGFACE_ENDPOINT`,
  `COHERE_ENDPOINT`, `DASHSCOPE_*`, `AZURE_*`, `VERTEX_AI_ENDPOINT`, and GCP project/credential vars.

### Present in `apps/api/.env.example`

- Backend baseline includes:
  `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `SILICONEFLOW_API_KEY`,
  `DEEPSEEK_API_KEY`, `GOOGLE_AI_API_KEY`, `DASHSCOPE_API_KEY`, `AZURE_API_KEY`,
  `AZURE_OPENAI_ENDPOINT`, `AZURE_API_VERSION`, `AZURE_DEPLOYMENT_ID`,
  `COLAB_WORKER_ENDPOINT`, `COLAB_WORKER_API_KEY`,
  `COLAB_WORKER_HEARTBEAT_ENABLED`, `COLAB_WORKER_HEARTBEAT_INTERVAL_SECONDS`.

### Not fully represented in examples (important)

- Some runtime-selectability vars are used in code but are not comprehensively documented in `apps/api/.env.example`:
  - `TOGETHER_API_KEY`
  - `HUGGINGFACE_API_KEY`
  - `COHERE_API_KEY`
  - `REPLICATE_API_KEY`
  - `OLLAMA_GCP_ENDPOINT`, `LLAMACPP_GCP_ENDPOINT`, `OLLAMA_LOCAL_ENDPOINT`
  - `COLAB_WORKER_ENDPOINT`, `COLAB_WORKER_API_KEY`
  - `VERTEX_AI_PROJECT` and credential variables (`GOOGLE_APPLICATION_CREDENTIALS`, `VERTEX_AI_SERVICE_ACCOUNT_JSON`, `GCP_SERVICE_ACCOUNT_KEY`)

## Notes for maintainers

- If `config/providers.toml` changes (provider IDs, `visible_providers`, env field names, or selectability flags), update this matrix in the same PR.
- Keep IDs canonical in docs and telemetry (`siliconeflow` remains canonical; legacy alias forms should not be persisted).
