# Goblin Assistant API Docs

This is the accurate entry point for the checked-in FastAPI backend.

## Base Behavior

- Framework: FastAPI
- App assembly: `../main.py`
- OpenAPI docs: `/docs`
- Health endpoint: `/health`
- Route versioning in code: mostly unversioned

## Actual Route Prefixes

These router groups are mounted by `../main.py`:

- `/api`
- `/auth`
- `/routing`
- `/execute`
- `/parse`
- `/raptor`
- `/chat`
- `/health`
- `/ops`
- `/search`
- `/settings`
- `/secrets`
- `/sandbox`
- `/api/privacy`
- `/debug`

## Notable Endpoints

### Auth

Defined in `../auth/router.py`:

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/google`
- `GET /auth/google/url`
- `POST /auth/google/callback`
- `POST /auth/passkey/challenge`
- `POST /auth/passkey/register`
- `POST /auth/passkey/auth`
- `POST /auth/validate`
- `GET /auth/me`

### Chat

Defined in `../chat_router.py`:

- `POST /chat/conversations`
- `GET /chat/conversations`
- `GET /chat/conversations/{conversation_id}`
- `PUT /chat/conversations/{conversation_id}/title`
- `DELETE /chat/conversations/{conversation_id}`
- `POST /chat/conversations/{conversation_id}/messages`
- `POST /chat/conversations/{conversation_id}/import`
- `POST /chat/completions`
- `POST /chat/contextual-chat`
- `POST /chat/stream`

### Health and Ops

Defined in `../health.py` and `../ops_router.py`:

- `GET /health`
- `GET /health/all`
- `GET /health/chroma/status`
- `GET /health/mcp/status`
- `GET /health/raptor/status`
- `GET /health/sandbox/status`
- `GET /health/cost-tracking`
- `GET /ops/health/summary`
- `GET /ops/providers/status`
- `GET /ops/performance/snapshot`

### Routing and task APIs

- `GET /routing/providers`
- `GET /routing/providers/{capability}`
- `POST /routing/route`
- `POST /api/chat`
- `POST /api/route_task`
- `POST /parse/`
- `POST /execute/`

### Search

Defined in `../search_router.py`:

- `POST /search/query`
- `GET /search/collections`
- `POST /search/collections/{collection_name}/add`
- `GET /search/collections/{collection_name}/documents`

### Sandbox

Defined in `../sandbox_api.py`:

- `POST /sandbox/submit`
- `GET /sandbox/status/{job_id}`
- `GET /sandbox/logs/{job_id}`
- `GET /sandbox/artifacts/{job_id}`
- `POST /sandbox/cancel/{job_id}`
- `GET /sandbox/health/status`

## Known Contract Drift

This backend documentation needs one explicit warning: the frontend code does not consistently call these unversioned paths.

Current examples of drift:

- frontend auth calls expect `/v1/auth/*`
- frontend provider registry expects `/v1/providers/models`
- frontend search calls expect `/v1/search/*`
- frontend sandbox calls expect `/v1/sandbox/*`
- Next proxy routes for `/api/models` and `/api/auth/validate` also expect `/v1/...`

Those expectations are visible in `../../src/api/apiClient.ts` and `../../src/pages/api`.

## Practical Guidance

- If you are testing the backend directly, use the unversioned paths listed here.
- If you are debugging frontend integration, check whether the frontend is calling `/v1/...` or a proxy route first.
- Chat and health are the most consistent local surfaces in the current repo state.
