"""
Kubernetes Admission Controller for Hardware Attestation Validation
Ensures only attested nodes can run sandbox workloads

This module is now a backward-compatible facade over the
attestation_webhook_pkg package. Everything is re-exported so
existing imports (e.g. ``import api.attestation_webhook as webhook``)
continue to work without changes.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request

from .attestation_webhook_pkg.middleware import (
    rate_limit,
    require_bearer_token,
    require_mtls,
)
from .attestation_webhook_pkg.routes import (
    handle_attest_node,
    handle_attestation_status,
    handle_health,
    handle_validate,
)

# Configure logging
logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("attestation.webhook.audit")

app = FastAPI(title="Sandbox Attestation Webhook")

# ── Route Registration ──────────────────────────────────────────────


@app.post("/validate")
@require_mtls
async def validate_admission(request: Request):
    """Admission controller webhook endpoint."""
    return await handle_validate(request)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return await handle_health()


@app.get("/attestation-status")
@rate_limit(limit_per_min=10)
async def get_attestation_status(request: Request):
    """DEPRECATED: Get current attestation status for all nodes."""
    return await handle_attestation_status(request)


@app.post("/attest-node")
@require_bearer_token
@rate_limit()
async def attest_node(request: Request):
    """Manually attest a node (for testing/admin purposes)."""
    return await handle_attest_node(request)


# ── Standalone entrypoint ───────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    # For development/testing
    # SECURITY NOTE: Deploy with mTLS in production
    logger.info("Starting attestation webhook server on 0.0.0.0:8443")
    uvicorn.run("api.attestation_webhook:app", host="0.0.0.0", port=8443, reload=True)
