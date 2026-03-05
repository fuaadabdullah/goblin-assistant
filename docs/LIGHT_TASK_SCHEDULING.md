---
title: "LIGHT TASK SCHEDULING"
description: "Light Task Scheduling Patterns"
---

# Light Task Scheduling Patterns

This document outlines three lightweight alternatives to Celery for simple periodic and request-triggered tasks in the Goblin Assistant backend.

## Overview

After analyzing all Celery tasks, we identified that some tasks are "heavy" (complex workflows, long-running operations) while others are "light" (simple periodic checks, quick cleanup operations). For light tasks, we've implemented three patterns:

1. **APScheduler + Redis Locks** - For in-app periodic scheduling
2. **FastAPI Background Tasks + Redis Locks** - For request-triggered operations
3. **Kubernetes CronJob** - For containerized periodic tasks

## Pattern 1: APScheduler + Redis Locks

**Use Case**: Periodic tasks that run within the main application process.

**Files**:

- `backend/scheduler.py` - APScheduler configuration and job registration
- `backend/jobs/provider_health.py` - Provider health checking job
- `backend/jobs/system_health.py` - System resource monitoring job
- `backend/jobs/cleanup.py` - Database cleanup job

**Key Features**:

- SQLAlchemy persistence for job schedules
- AsyncIO execution for non-blocking operations
- Redis distributed locks to prevent duplicate execution across multiple instances
- Graceful shutdown handling

**Example Usage**:

```python
from backend.scheduler import create_scheduler

scheduler = create_scheduler()
scheduler.start()

# Jobs are automatically registered and scheduled
```

## Pattern 2: FastAPI Background Tasks + Redis Locks

**Use Case**: Operations triggered by HTTP requests that should run asynchronously.

**Files**:

- `backend/api_router.py` - Added background task endpoints

**Key Features**:

- Built-in FastAPI BackgroundTasks for simple async execution
- Redis locks to prevent duplicate background tasks
- Status tracking for long-running operations
- Automatic cleanup of completed tasks

**Example Usage**:

```python

from fastapi import BackgroundTasks

@app.post("/cleanup")
async def trigger_cleanup(background_tasks: BackgroundTasks):
    background_tasks.add_task(simple_cleanup_task)
    return {"message": "Cleanup started in background"}
```

## Pattern 3: Kubernetes CronJob

**Use Case**: Periodic tasks in containerized environments where you want separate pod lifecycle.

**Files**:

- `backend/probe_worker.py` - Standalone worker script
- `k8s/provider-probe-cronjob.yaml` - CronJob manifest

**Key Features**:

- Completely separate from main application
- Independent scaling and resource allocation
- Built-in Kubernetes scheduling with `concurrencyPolicy: Forbid`
- Init containers for dependency waiting
- Proper resource limits and deadlines

**Example Usage**:

```bash
# Deploy the CronJob
kubectl apply -f k8s/provider-probe-cronjob.yaml

# Check CronJob status
kubectl get cronjobs
kubectl get jobs
```

## Configuration

### Environment Variables

All patterns support these environment variables:

- `REDIS_URL` - Redis connection string (required for locking)
- `DATABASE_URL` - Database connection string
- `LOG_LEVEL` - Logging level (INFO, DEBUG, etc.)
- `PROBE_TIMEOUT` - Timeout for health checks (default: 30s)

### Redis Lock Configuration

The Redis lock timeout is set to 5 minutes by default, which should be sufficient for most light tasks. Adjust in the code if needed:

```python

redis_lock = redis_client.lock(
    lock_key,
    timeout=300,  # 5 minutes
    blocking_timeout=0  # Don't block, fail immediately
)
```

## Migration from Celery

### Tasks Migrated

1. **Provider Health Checks** (`probe_all_providers`) - Moved to APScheduler
2. **System Health Monitoring** (`system_health_check`) - Moved to APScheduler
3. **Database Cleanup** (`cleanup_expired_data`) - Moved to APScheduler + FastAPI Background Tasks

### Heavy Tasks Remaining in Celery

- Complex inference workflows
- Multi-step data processing
- Long-running model operations
- Tasks requiring complex error handling and retries

## Monitoring and Debugging

### Health Endpoints

- `/health/scheduler` - APScheduler status
- `/cleanup/status` - Background task status

### Logs

All patterns include structured logging with task execution times and error details.

### Metrics

Consider adding metrics for:

- Task execution duration
- Success/failure rates
- Lock acquisition times

## Deployment Considerations

### APScheduler Pattern

- Best for single-instance or low-scale deployments
- Requires Redis for distributed locking
- Jobs persist across restarts

### FastAPI Background Tasks Pattern

- Good for request-triggered operations
- Limited to FastAPI application lifecycle
- Simple to implement and debug

### Kubernetes CronJob Pattern

- Ideal for containerized environments
- Independent scaling from main application
- Built-in Kubernetes monitoring and logging
- Requires Kubernetes cluster

## Testing

Each pattern includes test utilities:

```python
# Test APScheduler jobs
from backend.jobs.provider_health import probe_all_providers_job

# Test background tasks
from backend.api_router import simple_cleanup_task

# Test CronJob worker
python backend/probe_worker.py
```

## Migration Examples

### Minimal Wrapper: Single Provider Probe

**Old Celery Task:**

```python

@celery.task
def probe_provider(provider_id):
    # do network checks...
```

**New Patterns:**

**Pattern 1: APScheduler Job**

```python
# backend/probe_single_provider.py
def probe_single_provider_job(provider_id: int):
    """APScheduler job for individual provider probes."""
    result = asyncio.run(probe_provider_minimal(provider_id))
    return result
```

**Pattern 2: CronJob Script**

```python

# backend/probe_single_provider.py
def probe_provider_cronjob(provider_id: int):
    """Standalone wrapper with Redis locking for CronJob."""
    with redis_lock(f"provider_probe:{provider_id}"):
        result = asyncio.run(probe_provider_minimal(provider_id))
        return result
```

**Usage:**

- **Tiny tasks**: Use APScheduler job or CronJob wrapper
- **Distributed/scalable**: Keep as Celery if needed

**Files:**

- `backend/probe_single_provider.py` - Minimal wrapper implementation
- `k8s/single-provider-probe-cronjob.yaml` - CronJob manifest example

## Future Enhancements

- Add metrics collection for all patterns
- Implement circuit breakers for failing tasks
- Add task prioritization for APScheduler
- Create Helm charts for CronJob deployments
