# ADR-0004: Sandbox Architecture and Job Execution Model

## Status
accepted

## Date
2026-07-06

## Context
The sandbox executes untrusted user code, so it needs strong isolation, durable job state, and observable lifecycle behavior. The repo already uses an async job queue, Redis-backed state, and hardened container execution to keep submission responsive while work happens out of band.

## Decision
Implement the sandbox as an async job system backed by Redis/RQ and hardened Docker execution.

- `POST /api/v1/sandbox/run` enqueues work instead of executing code inline.
- Workers pull jobs from Redis/RQ, run them in restricted containers, and persist status/results.
- Non-log artifacts are uploaded to object storage with TTL-based cleanup.
- Metrics and health endpoints remain part of the sandbox contract so operational state is visible.

## Consequences
- User requests stay responsive while sandbox work runs asynchronously.
- Execution is isolated from the host through container and network restrictions.
- Job status, logs, and artifacts can be inspected after submission instead of being tied to a single request.

## Operational Notes
- Related ADRs: ADR-0002, ADR-0003.
- Sandbox route contracts, worker behavior, and artifact retention should be tested together because they form one operational system.
- Any future change to the execution model should preserve the queue/job/status contract or document a breaking migration separately.
