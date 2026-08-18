---
title: "LIGHT TASK SCHEDULING"
description: "Light task scheduling patterns"
---

# Light Task Scheduling Patterns

Use lightweight in-process or request-triggered patterns for simple periodic
and cleanup work. Do not add new Celery queues or revive deleted deployment
manifests for small jobs.

## Supported Patterns

| Pattern | Use Case |
|---|---|
| APScheduler plus Redis locks | Periodic jobs that can run inside the API process with distributed lock protection. |
| FastAPI background tasks plus Redis locks | Request-triggered work that should complete outside the immediate response path. |

## APScheduler Plus Redis Locks

Use this for periodic checks, cleanup, and low-volume maintenance tasks.

Requirements:

- `REDIS_URL` for distributed locking.
- Idempotent job body.
- Clear timeout and retry behavior.
- Structured logging for job start, success, failure, and skipped-lock cases.

## FastAPI Background Tasks Plus Redis Locks

Use this for request-triggered follow-up work that should not block the HTTP
response.

Requirements:

- Keep work bounded and observable.
- Use Redis locks for duplicate-sensitive operations.
- Return a clear accepted/status response to the caller.
- Promote long-running workflows to a proper service boundary instead of
  hiding them in background tasks.

## Retired Pattern

The previous Kubernetes CronJob pattern was removed with the repository's
Kubernetes manifests. If a separate container-scheduler target becomes
necessary again, introduce it as a new owned deployment capability with an ADR,
source manifests, and CI validation.

## Testing

For either supported pattern:

- Unit test the job body directly.
- Test lock acquisition and duplicate suppression.
- Test failure logging and retry behavior.
- Add a focused integration test when the job touches database, Redis, or
  provider state.
