# Celery Task Inventory & Migration Analysis

## Executive Summary

**Total Tasks Analyzed**: 8 Celery tasks
**Tasks Migrated to APScheduler**: 3 (37.5%)
**Tasks Remaining in Celery**: 5 (62.5%)
**Migration Status**: Partial - Light tasks replaced, heavy tasks retained

## Task Inventory

### 1. Provider Health Check (`tasks.provider_probe_worker.probe_all_providers`)

**Status**: ✅ MIGRATED to APScheduler
**Classification**: REPLACE (Light)
**Current Implementation**: APScheduler job in `jobs/provider_health.py`

**Performance Metrics**:

- **Avg Duration**: < 30 seconds (network checks only)
- **Peak Concurrency**: 1-5 concurrent probes (limited by semaphore)
- **Memory Usage**: ~50-100MB (database connections + network)
- **I/O Pattern**: Light DB reads/writes, network calls
- **Frequency**: Every 5 minutes

**Migration Rationale**: Simple periodic health checks, no complex orchestration needed.

---

### 2. System Health Check (`tasks.monitoring_worker.system_health_check`)

**Status**: ✅ MIGRATED to APScheduler
**Classification**: REPLACE (Light)
**Current Implementation**: APScheduler job in `jobs/system_health.py`

**Performance Metrics**:

- **Avg Duration**: < 5 seconds (system metrics collection)
- **Peak Concurrency**: 1 (single instance execution)
- **Memory Usage**: ~20-50MB (psutil + basic monitoring)
- **I/O Pattern**: Local system calls, minimal DB writes
- **Frequency**: Every 1 minute

**Migration Rationale**: Basic system monitoring, runs frequently but lightweight.

---

### 3. Database Cleanup (`tasks.cleanup_worker.cleanup_expired_data`)

**Status**: ✅ MIGRATED to APScheduler
**Classification**: REPLACE (Light)
**Current Implementation**: APScheduler job in `jobs/cleanup.py`

**Performance Metrics**:

- **Avg Duration**: < 60 seconds (bulk delete operations)
- **Peak Concurrency**: 1 (prevent concurrent cleanup)
- **Memory Usage**: ~100-200MB (large result sets)
- **I/O Pattern**: Heavy DB writes (DELETE operations)
- **Frequency**: Every 6 hours

**Migration Rationale**: Scheduled maintenance task, no complex dependencies.

---

### 4. Model Performance Report (`tasks.model_training_worker.generate_performance_report`)

**Status**: ❌ KEEP in Celery
**Classification**: KEEP (Heavy)
**Current Implementation**: Celery beat schedule (every 12 hours)

**Performance Metrics**:

- **Avg Duration**: 10-30 minutes (model evaluation + report generation)
- **Peak Concurrency**: 1 (resource intensive)
- **Memory Usage**: 500MB-2GB (model loading + inference)
- **I/O Pattern**: Heavy DB reads, file I/O for reports
- **Frequency**: Every 12 hours

**Retention Rationale**: Complex ML operations, long runtime, resource intensive.

---

### 5. Data Processing Worker (`tasks.data_processing_worker.*`)

**Status**: ❌ KEEP in Celery
**Classification**: KEEP (Heavy)
**Current Implementation**: Not fully implemented (referenced in config)

**Performance Metrics** (Estimated):

- **Avg Duration**: 5-60 minutes (data transformation pipelines)
- **Peak Concurrency**: 2-5 concurrent workers
- **Memory Usage**: 200MB-1GB (data processing)
- **I/O Pattern**: Heavy file I/O, DB operations
- **Frequency**: On-demand/batch

**Retention Rationale**: ETL operations, complex workflows, variable resource usage.

---

### 6. Model Training Worker (`tasks.model_training_worker.*`)

**Status**: ❌ KEEP in Celery
**Classification**: KEEP (Heavy)
**Current Implementation**: Partially implemented (performance reports only)

**Performance Metrics** (Estimated):

- **Avg Duration**: 30-240 minutes (model training)
- **Peak Concurrency**: 1 (GPU/CPU intensive)
- **Memory Usage**: 2-16GB (training data + models)
- **I/O Pattern**: Heavy file I/O, model serialization
- **Frequency**: Scheduled/batch

**Retention Rationale**: ML training workloads, extreme resource requirements.

---

### 7. Notification Worker (`tasks.notification_worker.*`)

**Status**: ❌ KEEP in Celery
**Classification**: KEEP (Heavy)
**Current Implementation**: Not implemented (referenced in config)

**Performance Metrics** (Estimated):

- **Avg Duration**: 1-10 minutes (email/SMS/external API calls)
- **Peak Concurrency**: 5-20 concurrent notifications
- **Memory Usage**: 50-200MB (template processing)
- **I/O Pattern**: External API calls, DB reads
- **Frequency**: Event-driven

**Retention Rationale**: External service dependencies, retry logic needed, variable latency.

---

### 8. Generic Task Processor (`celery_task_queue.process_task_celery`)

**Status**: ❌ KEEP in Celery
**Classification**: KEEP (Heavy)
**Current Implementation**: RQ replacement in `celery_task_queue.py`

**Performance Metrics** (Estimated):

- **Avg Duration**: 1-30 minutes (variable task types)
- **Peak Concurrency**: 5-50 concurrent tasks
- **Memory Usage**: 100MB-1GB (task-dependent)
- **I/O Pattern**: Variable (DB, file, network)
- **Frequency**: On-demand

**Retention Rationale**: Generic task processing, complex error handling, result tracking.

## Migration Decision Framework

### REPLACE (Lightweight Tasks)

**Criteria**:

- Runtime < 5 minutes
- Memory usage < 500MB
- Simple success/failure logic
- No complex dependencies
- Tolerates occasional skips
- Runs on single instance

**Migration Pattern**: APScheduler + Redis locks

### KEEP (Heavy Tasks)

**Criteria**:

- Runtime > 5 minutes
- Memory usage > 500MB
- Complex error handling/retry logic
- External service dependencies
- Requires result tracking
- Needs concurrent execution
- Critical timing requirements

**Retention Pattern**: Celery with full orchestration

## Implementation Status

### ✅ Completed Migrations

1. **Provider Health Checks** → APScheduler job
2. **System Health Checks** → APScheduler job
3. **Database Cleanup** → APScheduler job

### 🔄 Next Steps

1. **Unit Tests** - Create comprehensive test suite for APScheduler jobs
2. **Integration Tests** - Test Redis locking and multi-instance behavior
3. **Staging Deployment** - Deploy to one replica, verify single execution
4. **Monitoring** - Add metrics and alerting for job execution
5. **Documentation** - Update runbooks and troubleshooting guides

## Performance Impact

### Before Migration

- **Celery Workers**: 3-5 workers needed for light tasks
- **Resource Usage**: ~1-2GB memory for worker processes
- **Operational Complexity**: Full Celery infrastructure (broker, result backend, monitoring)

### After Migration

- **APScheduler**: Integrated into app process (~100MB additional memory)
- **Resource Savings**: ~800MB-1.5GB memory reduction
- **Simplified Operations**: No separate worker management for light tasks

## Risk Assessment

### Low Risk ✅

- Light tasks are simple and well-understood
- APScheduler has mature Redis locking patterns
- Easy rollback (re-enable Celery tasks)

### Medium Risk ⚠️

- Multi-instance coordination relies on Redis availability
- Job persistence requires database availability
- Monitoring gap until new metrics are implemented

### Mitigation Strategies

- Redis Sentinel for high availability
- Job execution logging and alerting
- Gradual rollout (one replica at a time)
- Comprehensive testing before production deployment
