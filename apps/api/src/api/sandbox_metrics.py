"""
Prometheus metrics for sandbox operations
Provides comprehensive monitoring and alerting capabilities
"""

import time
from typing import Dict, Any
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import os

# Sandbox job metrics
SANDBOX_JOBS_SUBMITTED = Counter(
    'sandbox_jobs_submitted_total',
    'Total number of sandbox jobs submitted',
    ['language', 'status']
)

SANDBOX_JOBS_RUNNING = Gauge(
    'sandbox_jobs_running',
    'Number of currently running sandbox jobs'
)

SANDBOX_JOB_DURATION = Histogram(
    'sandbox_job_duration_seconds',
    'Time taken to execute sandbox jobs',
    ['language', 'exit_code'],
    buckets=[1, 5, 10, 30, 60, 120, 300]  # 1s to 5min buckets
)

SANDBOX_JOB_FAILURES = Counter(
    'sandbox_job_failures_total',
    'Total number of failed sandbox jobs',
    ['failure_type', 'language']
)

SANDBOX_CONTAINER_KILLS = Counter(
    'sandbox_container_kills_total',
    'Total number of containers killed due to timeouts or errors',
    ['reason']
)

SANDBOX_QUEUE_DEPTH = Gauge(
    'sandbox_queue_depth',
    'Current depth of the sandbox job queue'
)

# Additional useful metrics
SANDBOX_ARTIFACTS_UPLOADED = Counter(
    'sandbox_artifacts_uploaded_total',
    'Total number of artifacts uploaded to storage',
    ['result']  # success/failure
)

SANDBOX_ARTIFACTS_SIZE = Histogram(
    'sandbox_artifacts_size_bytes',
    'Size distribution of uploaded artifacts',
    buckets=[1024, 10240, 102400, 1048576, 10485760]  # 1KB to 10MB
)

SANDBOX_CLEANUP_RUNS = Counter(
    'sandbox_cleanup_runs_total',
    'Total number of artifact cleanup runs',
    ['result']  # success/failure
)

SANDBOX_CLEANUP_DELETED = Counter(
    'sandbox_cleanup_artifacts_deleted_total',
    'Total number of artifacts deleted during cleanup'
)

# Job tracking for duration measurement
_active_jobs: Dict[str, Dict[str, Any]] = {}

def record_job_submitted(job_id: str, language: str):
    """Record when a job is submitted to the queue"""
    SANDBOX_JOBS_SUBMITTED.labels(language=language, status='queued').inc()
    SANDBOX_QUEUE_DEPTH.inc()

    _active_jobs[job_id] = {
        'language': language,
        'submitted_at': time.time(),
        'status': 'queued'
    }

def record_job_started(job_id: str):
    """Record when a job starts execution"""
    if job_id in _active_jobs:
        _active_jobs[job_id]['started_at'] = time.time()
        _active_jobs[job_id]['status'] = 'running'

        # Update counters
        SANDBOX_QUEUE_DEPTH.dec()
        SANDBOX_JOBS_RUNNING.inc()

def record_job_completed(job_id: str, exit_code: int, execution_time: float = None):
    """Record when a job completes successfully"""
    if job_id in _active_jobs:
        job_info = _active_jobs[job_id]

        # Calculate duration if not provided
        if execution_time is None:
            started_at = job_info.get('started_at')
            if started_at:
                execution_time = time.time() - started_at

        # Record metrics
        if execution_time:
            SANDBOX_JOB_DURATION.labels(
                language=job_info['language'],
                exit_code=str(exit_code)
            ).observe(execution_time)

        # Update status counters
        SANDBOX_JOBS_SUBMITTED.labels(
            language=job_info['language'],
            status='completed'
        ).inc()

        SANDBOX_JOBS_RUNNING.dec()

        # Clean up tracking
        del _active_jobs[job_id]

def record_job_failed(job_id: str, failure_type: str, execution_time: float = None):
    """Record when a job fails"""
    if job_id in _active_jobs:
        job_info = _active_jobs[job_id]

        # Calculate duration if not provided
        if execution_time is None:
            started_at = job_info.get('started_at')
            if started_at:
                execution_time = time.time() - started_at

        # Record metrics
        if execution_time:
            SANDBOX_JOB_DURATION.labels(
                language=job_info['language'],
                exit_code='-1'  # Failed jobs
            ).observe(execution_time)

        # Update failure counters
        SANDBOX_JOB_FAILURES.labels(
            failure_type=failure_type,
            language=job_info['language']
        ).inc()

        SANDBOX_JOBS_SUBMITTED.labels(
            language=job_info['language'],
            status='failed'
        ).inc()

        SANDBOX_JOBS_RUNNING.dec()

        # Clean up tracking
        del _active_jobs[job_id]

def record_job_cancelled(job_id: str):
    """Record when a job is cancelled"""
    if job_id in _active_jobs:
        job_info = _active_jobs[job_id]

        SANDBOX_JOBS_SUBMITTED.labels(
            language=job_info['language'],
            status='cancelled'
        ).inc()

        # If it was running, decrement running counter
        if job_info['status'] == 'running':
            SANDBOX_JOBS_RUNNING.dec()
        else:
            # If it was queued, decrement queue counter
            SANDBOX_QUEUE_DEPTH.dec()

        # Clean up tracking
        del _active_jobs[job_id]

def record_container_killed(reason: str):
    """Record when a container is killed"""
    SANDBOX_CONTAINER_KILLS.labels(reason=reason).inc()

def record_artifact_upload(success: bool, size_bytes: int = 0):
    """Record artifact upload metrics"""
    result = 'success' if success else 'failure'
    SANDBOX_ARTIFACTS_UPLOADED.labels(result=result).inc()

    if success and size_bytes > 0:
        SANDBOX_ARTIFACTS_SIZE.observe(size_bytes)

def record_cleanup_run(success: bool, deleted_count: int = 0):
    """Record cleanup run metrics"""
    result = 'success' if success else 'failure'
    SANDBOX_CLEANUP_RUNS.labels(result=result).inc()

    if success and deleted_count > 0:
        SANDBOX_CLEANUP_DELETED.inc(deleted_count)

def update_queue_depth(current_depth: int):
    """Update the current queue depth gauge"""
    SANDBOX_QUEUE_DEPTH.set(current_depth)

def get_metrics_text() -> str:
    """Get metrics in Prometheus text format"""
    return generate_latest().decode('utf-8')

def get_metrics_endpoint():
    """FastAPI endpoint for Prometheus metrics"""
    return Response(
        content=get_metrics_text(),
        media_type=CONTENT_TYPE_LATEST
    )

# Utility functions for integration
def get_failure_type_from_error(error: str) -> str:
    """Categorize failure types from error messages"""
    error_lower = error.lower()

    if 'timeout' in error_lower:
        return 'timeout'
    elif 'memory' in error_lower or 'oom' in error_lower:
        return 'resource_limit'
    elif 'network' in error_lower:
        return 'network_error'
    elif 'permission' in error_lower or 'security' in error_lower:
        return 'security_error'
    elif 'compilation' in error_lower or 'syntax' in error_lower:
        return 'compilation_error'
    elif 'container' in error_lower or 'docker' in error_lower:
        return 'container_error'
    else:
        return 'unknown'

# Integration with RQ for queue monitoring
def update_rq_metrics(queue):
    """Update metrics based on RQ queue status"""
    try:
        # Get queue statistics
        queued_count = len(queue)
        update_queue_depth(queued_count)

        # Get worker information (if available)
        # This would need access to RQ registry
        # For now, we rely on the job lifecycle tracking

    except Exception as e:
        print(f"⚠️  Failed to update RQ metrics: {e}")

# Alerting helpers - these thresholds should match your alerting rules
ALERT_THRESHOLDS = {
    'job_failure_rate_threshold': 0.05,  # 5% failure rate over 5 minutes
    'queue_depth_threshold': 50,  # Queue depth > 50
    'job_duration_p95_threshold': 240,  # 4 minutes (90% of 5min timeout)
}

def check_alerts() -> Dict[str, Any]:
    """
    Check current metrics against alerting thresholds
    Returns alerts that should be triggered
    """
    alerts = []

    # This is a simplified check - in production you'd want more sophisticated
    # time-window based alerting logic

    try:
        # Get current failure rate (simplified - would need proper time windows)
        # This is just for demonstration

        current_queue_depth = SANDBOX_QUEUE_DEPTH._value
        if current_queue_depth > ALERT_THRESHOLDS['queue_depth_threshold']:
            alerts.append({
                'alert_name': 'SandboxQueueDepthHigh',
                'severity': 'warning',
                'message': f'Queue depth is {current_queue_depth}, above threshold {ALERT_THRESHOLDS["queue_depth_threshold"]}',
                'value': current_queue_depth
            })

    except Exception as e:
        print(f"⚠️  Error checking alerts: {e}")

    return alerts