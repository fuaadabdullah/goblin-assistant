---
description: 'Short architecture overview and process flow for GoblinOS Assistant'
---

# Architecture Overview — GoblinOS Assistant

This short document provides a concise architecture diagram and a quick request/response process flow for the GoblinOS Assistant.

> See `CORE_IDENTITY.md` for product-level messaging, core characteristics, and a short pitch describing GoblinOS Assistant's purpose and differentiators.

## Mermaid Diagram

```mermaid
graph LR
  subgraph Frontend
    U[User/Client] --> |HTTP / Websocket| FE(React + Vite UI)
  end

  subgraph API
    FE --> API[FastAPI (backend/main.py)]
    API --> GW[Gateway Service (gateway_service.py)]
    GW --> RS[RoutingService (services/routing.py)]
    RS -->|Local| OLLA[Ollama / LlamaCPP]
    RS -->|Cloud| OPENAI(OpenAI) & ANTHROPIC(Anthropic) & DEEPSEEK(DeepSeek) & GROK(Grok)
    RS --> RAG[RAG/Vector DB (services/rag_service.py)]
    API --> DB[DB (goblin_assistant.db or Postgres) (database.py)]
    API --> REDIS[Redis (cache, rate limiting, Celery broker)]
    API --> SCHED[APScheduler (scheduler.py) / Celery (celery_app.py)]
    API --> MON[Monitoring - Sentry, OpenTelemetry, Fly/Vercel metrics]
  end

  subgraph Background
    SCHED -.-> Jobs(Health probes, cleanup, provider probes)
    Celery -.-> LongRunning(Training, batch tasks, ETL)
  end

  MON --> |logs & telemetry| API
  REDIS --> |broker/cache| Celery
  DB --> |persistence| API
```

## Request Flow (Quick)

1. User sends a chat message from the frontend.
2. Frontend sends the request to the FastAPI backend (`/v1/chat` or related route).
3. Gateway service performs budget checks, token estimates, and request classification (`gateway_service.py`).
4. RoutingService (Raptor/`services/routing.py`) selects the provider and decides if RAG should be applied.
5. If RAG is enabled, the RAG service retrieves vector entries and merges them into prompt construction (`services/rag_service.py`).
6. The chosen provider adapter (Ollama / OpenAI / Anthropic / Grok / DeepSeek) is invoked and returns a response (`providers/*`).
7. The response is run through output verification, token accounting, and returned to the client.
8. Background jobs update monitoring, metrics, and perform health probes and cleanup tasks.

See the simplified sequence diagram in `SEQUENCE_DIAGRAM.md` for a compact view of the request routing sequence.

## Key files & locations

- `backend/main.py` — FastAPI app, middleware & router wiring
- `backend/gateway_service.py` — Budgeting & request classification
- `backend/services/routing.py` — Provider selection & routing logic
- `backend/services/rag_service.py` — RAG integration and vector retrieval
- `backend/providers/*` — Provider adapters (OpenAI, Anthropic, Ollama, etc.)
- `backend/scheduler.py` — APScheduler with Redis locks (lightweight jobs)
- `backend/celery_app.py` — Celery configuration for heavy and distributed jobs
- `backend/debugger` — Debugging endpoints and model routing
- `src/` — Frontend code (React + Vite + TypeScript)

## Notes

- The diagram intentionally omits minor subsystems (auth, API keys, dashboard endpoints, and infra-specific overlay services) for clarity.
- For detailed backend docs, see `backend/docs/README.md` and the per-area docs under `backend/docs/`.

## Runbook: Adding a Provider or Updating Routing

Follow these steps when you want to add a new provider adapter (e.g., partner SDK) or update routing rules:

### 1) Implement the adapter

- Create a new adapter in `backend/providers/` (follow existing adapters like `openai_adapter.py` as a template).
- Use `backend/providers/base_adapter.py` or `BaseAdapter` where possible for consistent interface.
- Add configuration parsing in `backend/config` and update `backend/.env.example` to include required env vars.

### 2) Register the provider

- Add the provider to `backend/providers/registry.py` so `RoutingService` can discover it.
- Add provider metadata and a safe default for `is_enabled` flags in `seed_routing.py` or `settings` as applicable.

### 3) Update routing logic & selection

- Modify `backend/services/routing.py` or `gateway_service.py` only if provider selection needs new signals (latency, cost, capabilities).
- Prefer a feature-flagged rollout and keep a fallback provider for high availability.

### 4) Add tests

- Add unit tests for the adapter and mock provider in `backend/providers/tests/`.
- Add integration tests in `backend/test_api_providers.py` and, if necessary, `test_routing_endpoints.py`.
- Verify the new provider is covered by `test_local_model_integration.py` or `test_model_comparison.py` as needed.

### 5) Add documentation

- Update `backend/docs/ENVIRONMENT_VARIABLES.md`, `backend/docs/ENDPOINT_AUDIT.md`, and `apps/goblin-assistant/docs/ARCHITECTURE_OVERVIEW.md` to list the new provider.
- Add provider-specific notes and any required keys to `backend/.env.example`.

### 6) CI & Deployment

- Ensure unit & integration tests pass in CI.
- If adding infra requirements, update `infra/` (e.g., to add secrets/credentials in Vault) and relevant deployment docs.

### 7) Monitoring & Alerts

- Add provider metrics (latency, error rate) to `backend/monitoring` or Prometheus integrations.
- Add or update provider health probes under `jobs/provider_health` and verify `scheduler.py` registers them.

### Troubleshooting

- Run `probe_single_provider.py` and `probe_worker.py` to diagnose connectivity and latency issues.
- Inspect `logs/` and Sentry for stack traces and timeouts.
- Switch to a fallback provider if errors or regressions persist during rollout.

---
