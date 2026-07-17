# Feature Status

This file describes what the current `goblin-assistant` codebase implements, not the intended roadmap.

## Frontend Modules

| Area | Status | What the code shows |
| --- | --- | --- |
| Chat UI | Working path | Next.js chat page, provider selector, thread list, prompt composer, token/cost display, and backend conversation integration via `/chat/conversations/*` |
| Prompt generation proxy | Working path | `apps/web/app/api/generate/route.ts` forwards frontend prompt requests to backend `/api/v1/api/chat` |
| Startup flow | Working path | `apps/web/src/features/startup/hooks/useStartupFlow.ts` boots auth, routing info, and provider registry before redirecting |
| Auth screens | Working path | Login/register UI, Google OAuth UI, Turnstile, passkey UI, and frontend auth bootstrap all exist; the browser talks to `/api/auth/validate` for the proxy path and `/api/v1/auth/*` for backend auth operations |
| Search UI | Working path | Search routes are wired at `app/search/page.tsx` and `app/chat/page.tsx`, using `features/search/*` with backend calls to `/api/v1/search/collections` and `/api/v1/search/query`; the backend search implementation is text-first rather than full semantic retrieval |
| Sandbox UI | Working path | Guest mode and sandbox screen exist, and the frontend client handles the job-based `/api/v1/sandbox/run` flow with logs fetched from `/api/v1/sandbox/jobs/{job_id}/logs`; the backend also keeps `/sandbox/submit`, `/sandbox/status/{job_id}`, and related compatibility aliases |
| Agent loop UI | Working path | A dedicated `/agent` screen can submit self-development tasks, poll task state, and surface PR links from the new `/api/v1/agent/task` workflow |
| Admin/provider screens | Working path | Admin pages and provider manager UI exist; provider registry loading uses `/api/models` -> backend `/api/v1/providers/models`, and provider health/state routes are also wired |
| Account page | Working path | Account/profile UI exists and save calls target `/api/v1/account/profile` and `/api/v1/account/preferences`, which are present in the backend contract |
| Help/support form | Working path | Help page exists and can display startup diagnostics, and support form submission targets `/api/v1/support/message` |

## Backend Capabilities

| Area | Status | What the code shows |
| --- | --- | --- |
| Auth | Implemented | Email/password, JWT validation, Google OAuth helpers, CSRF token issuance, passkey challenge/register/auth endpoints in `api/auth/router.py` |
| Conversations and chat | Implemented | Conversation CRUD, message send, OpenAI-style completions, contextual chat, semantic chat, and streaming endpoints in `api/chat_router.py` and `api/semantic_chat_router.py` |
| Routing/orchestration | Implemented | Routing endpoints under `/routing`, task/orchestration endpoints under `/api`, `/parse`, and `/execute` |
| Self-development agent loop | Implemented | `/api/v1/agent/task` persists lifecycle state, derives a persistent Sprite workspace, normalizes GitHub issue triggers, and accepts worker callbacks for planning/editing/testing/repair/PR creation progress |
| Health/ops/debug | Implemented | Health, provider checks, ops snapshots, observability debug endpoints, and routing analytics endpoints are included in `apps/api/src/api/main.py` |
| Provider registry / models | Implemented | Provider metadata, model inventory, and provider health routes are exposed through `/api/v1/providers/*` and the frontend proxy `/api/models` |
| Search backend | Implemented but simple | In-memory collection storage with text matching, not a full vector-search pipeline by default |
| Privacy endpoints | Implemented | GDPR/CCPA-style export/delete/summary/consent routes under `/api/privacy` |
| Secrets management | Implemented | Secrets router and adapter initialization are wired in the FastAPI app |
| Sandbox backend | Implemented with compatibility aliases | RQ/Redis-backed sandbox job submission and artifact endpoints exist, and the request/response aliases are aligned with the current frontend client API |

## Known Integration Mismatches

- The frontend uses both direct backend calls and thin Next API proxies.
- Most frontend infrastructure outside chat expects versioned `/api/v1/...` endpoints.
- The checked-in FastAPI app mounts public backend routers under `/api/v1`.
- `/api/models` and `/api/auth/validate` are intentional proxy endpoints, not backend mounts.

The practical result is that chat is the cleanest end-to-end path in this checkout, while several other screens are present but need contract alignment before they are reliable locally.
