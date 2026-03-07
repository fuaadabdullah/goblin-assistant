# Feature Status

This file describes what the current `goblin-assistant` codebase implements, not the intended roadmap.

## Frontend Modules

| Area | Status | What the code shows |
| --- | --- | --- |
| Chat UI | Working path | Next.js chat page, provider selector, thread list, prompt composer, token/cost display, and backend conversation integration via `/chat/conversations/*` |
| Prompt generation proxy | Working path | `src/pages/api/generate.ts` forwards frontend prompt requests to backend `/api/chat` |
| Startup flow | Working path | `src/features/startup/hooks/useStartupFlow.ts` boots auth, routing info, and provider registry before redirecting |
| Auth screens | Partial | Login/register UI, Google OAuth UI, Turnstile, and passkey UI exist; frontend currently calls `/v1/auth/*`, while local FastAPI routers are mounted at `/auth/*` |
| Search UI | Partial | Search screen and hooks exist, but the frontend expects `/v1/search/*` and different payload/response shapes than `api/search_router.py` exposes |
| Sandbox UI | Partial | Guest mode and sandbox screen exist, but the frontend expects `/v1/sandbox/run` and `/v1/sandbox/jobs`; the local backend exposes `/sandbox/submit`, `/sandbox/status/{job_id}`, and related job endpoints |
| Admin/provider screens | Partial | Admin pages and provider manager UI exist, but provider registry loading depends on `/api/models` -> backend `/v1/providers/models`, which is not implemented in `api/` |
| Account page | Partial | Account/profile UI exists, but frontend save calls expect `/v1/account/profile` and `/v1/account/preferences`; no matching backend router is checked in |
| Help/support form | Partial | Help page exists and can display startup diagnostics, but support form submission expects `/v1/support/message`; no matching backend route is checked in |

## Backend Capabilities

| Area | Status | What the code shows |
| --- | --- | --- |
| Auth | Implemented | Email/password, JWT validation, Google OAuth helpers, CSRF token issuance, passkey challenge/register/auth endpoints in `api/auth/router.py` |
| Conversations and chat | Implemented | Conversation CRUD, message send, OpenAI-style completions, contextual chat, semantic chat, and streaming endpoints in `api/chat_router.py` and `api/semantic_chat_router.py` |
| Routing/orchestration | Implemented | Routing endpoints under `/routing`, task/orchestration endpoints under `/api`, `/parse`, and `/execute` |
| Health/ops/debug | Implemented | Health, provider checks, ops snapshots, observability debug endpoints, and routing analytics endpoints are included in `api/main.py` |
| Search backend | Implemented but simple | In-memory collection storage with text matching, not a full vector-search pipeline by default |
| Privacy endpoints | Implemented | GDPR/CCPA-style export/delete/summary/consent routes under `/api/privacy` |
| Secrets management | Implemented | Secrets router and adapter initialization are wired in the FastAPI app |
| Sandbox backend | Implemented but separate contract | RQ/Redis-backed sandbox job submission and artifact endpoints exist, but they are not aligned with the current frontend client API |

## Known Integration Mismatches

- The frontend uses both direct backend calls and thin Next API proxies.
- Most frontend infrastructure outside chat expects versioned `/v1/...` endpoints.
- The checked-in FastAPI app mounts most routers without `/v1`.
- `/api/models` and `/api/auth/validate` expect versioned backend routes that are not defined in `api/main.py`.

The practical result is that chat is the cleanest end-to-end path in this checkout, while several other screens are present but need contract alignment before they are reliable locally.
