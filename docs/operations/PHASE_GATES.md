# Phase Gates

These gates are the recommended order for bringing the system up against the real repo.
They are intentionally strict so we only advance when the current layer is proven in
production-like conditions.

## Gate 1: Baseline Chat Loop

Stand up:
- Supabase
- Upstash Redis
- FastAPI backend
- Next.js frontend
- one DashScope model

Proceed only when:
- a deployed chat message round-trips end to end
- the conversation state persists in the cloud data layer
- minimal CI is running on the branch

## Gate 2: Smart Routing

Add:
- LiteLLM routing across DashScope + Vertex
- fallback chains
- heuristic task classification
- per-call cost and latency logging

Proceed only when:
- cost and latency are logged for every routed call
- a forced provider outage demonstrably triggers fallback
- routing decisions are persisted for later tuning

## Gate 3: Agent Loop

Add:
- Aider-in-Sprite architect/editor loop
- test-run-repair retries
- PyGithub PR automation

Proceed only when:
- one agent-authored PR passes CI
- the PR is merged by hand

## Change Triggers

Use these as conditional escalations, not defaults:
- stay on Sprite when agent runs need more than 24 hours of persistence or heavy parallelism
- move Vercel from Hobby to Pro, or front it with Cloudflare, if Hobby limits become real blockers
- move Supabase to Pro if pausing materially hurts the workflow

