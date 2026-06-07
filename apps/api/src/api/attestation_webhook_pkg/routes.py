"""Route handlers for the attestation webhook."""

import logging
import os
from datetime import date as _date
from typing import Any, Dict

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from .auth import get_verified_identity
from .models import AdmissionReview, validate_pod_attestation

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("attestation.webhook.audit")

# Sunset date for /attestation-status — after this date the endpoint
# returns 410 Gone unless ATTEST_DEPRECATION_KILL_OVERRIDE is set.
_ATTEST_STATUS_KILL_DATE = "2026-08-25"
_ATTEST_STATUS_SUNSET_LINK = "https://docs.goblin.assistant/migration/attestation-validate"


def create_admission_denied_event(pod: Dict[str, Any], reason: str):
    """Create a Kubernetes event for denied admission"""
    try:
        from kubernetes import client, config
    except ImportError as exc:
        logger.debug("kubernetes_client_unavailable", exc_info=exc)
        return

    ConfigException = getattr(config, "ConfigException", Exception)
    try:
        config.load_incluster_config()
    except ConfigException as exc:
        logger.debug("could_not_load_incluster_config", exc_info=exc)

    v1 = client.CoreV1Api()

    pod_name = pod.get("metadata", {}).get("name", "unknown")
    namespace = pod.get("metadata", {}).get("namespace", "sandbox")

    kclient: Any = client
    event_cls = getattr(kclient, "V1Event")
    event = event_cls(
        metadata=kclient.V1ObjectMeta(
            name=f"sandbox-attestation-denied-{pod_name}", namespace=namespace
        ),
        involved_object=kclient.V1ObjectReference(kind="Pod", name=pod_name, namespace=namespace),
        reason="AttestationValidationFailed",
        message=f"Pod admission denied due to attestation failure: {reason}",
        type="Warning",
        source=kclient.V1EventSource(component="sandbox-attestation-webhook"),
        first_timestamp=None,
        last_timestamp=None,
    )

    ApiException = getattr(getattr(client, "exceptions", None), "ApiException", None)

    if ApiException:
        try:
            v1.create_namespaced_event(namespace, event)
        except ApiException as exc:
            logger.exception("create_namespaced_event_api_error", exc_info=exc)
    else:
        try:
            v1.create_namespaced_event(namespace, event)
        except Exception as exc:
            logger.exception("create_admission_event_failed", extra={"error": str(exc)})


async def handle_validate(request: Request):
    """Admission controller webhook endpoint.

    SECURITY: Validates requests from Kubernetes API server via mTLS.
    Returns generic error messages to prevent information leakage.
    Logs all admission decisions for audit trail.
    """
    uid = "unknown"
    try:
        body = await request.json()
        admission_review = AdmissionReview(**body)

        uid = admission_review.request.get("uid", "unknown")
        pod = admission_review.request.get("object", {})

        pod_name = pod.get("metadata", {}).get("name", "unknown")
        namespace = pod.get("metadata", {}).get("namespace", "unknown")
        audit_logger.info(
            "admission_review_received",
            extra={"uid": uid, "pod": pod_name, "namespace": namespace},
        )

        validation = validate_pod_attestation(pod)

        response = {
            "uid": uid,
            "allowed": validation["allowed"],
            "status": {"message": validation["message"]},
        }

        if not validation["allowed"]:
            response["status"]["code"] = 403
            response["status"]["reason"] = "Forbidden"

            audit_logger.warning(
                "admission_denied",
                extra={
                    "uid": uid,
                    "reason": validation["message"],
                    "pod": pod_name,
                    "namespace": namespace,
                },
            )

            create_admission_denied_event(pod, validation["message"])
        else:
            audit_logger.info(
                "admission_approved",
                extra={"uid": uid, "pod": pod_name, "namespace": namespace},
            )

        admission_response = {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": response,
        }

        return JSONResponse(content=admission_response)

    except (ValueError, TypeError, KeyError) as e:
        logger.exception("webhook_validation_input_error", exc_info=e)

        admission_response = {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": {
                "uid": uid,
                "allowed": False,
                "status": {"code": 400, "message": "Invalid admission review payload"},
            },
        }

        audit_logger.warning("admission_input_error", extra={"uid": uid})
        return JSONResponse(content=admission_response, status_code=400)


async def handle_health(request: Request):
    """Health check endpoint"""
    try:
        from ..attestation_service import get_attestation_service

        service = get_attestation_service()
        attested_count = len(service.list_attested_nodes())

        return {
            "status": "healthy",
            "attested_nodes": attested_count,
            "service": "attestation-webhook",
        }
    except Exception as exc:
        logger.exception("health_check_failed", exc_info=exc)
        raise HTTPException(status_code=503, detail="Health check failed") from exc


async def handle_attestation_status(request: Request):
    """DEPRECATED: Get current attestation status for all nodes."""
    from ..attestation_service import get_attestation_service

    # Kill-date guard
    kill_override = os.getenv("ATTEST_DEPRECATION_KILL_OVERRIDE", "").lower()
    if kill_override not in ("true", "1", "yes"):
        if _date.today() >= _date.fromisoformat(_ATTEST_STATUS_KILL_DATE):
            audit_logger.warning(
                "attestation_status_kill_date_reached",
                extra={
                    "kill_date": _ATTEST_STATUS_KILL_DATE,
                    "path": request.url.path,
                },
            )
            raise HTTPException(
                status_code=410,
                detail="This endpoint was deprecated and has been removed. Use /validate instead.",
            )

    extra = {
        "path": request.url.path,
        "method": request.method,
        "client_host": (request.client.host if request.client else "unknown"),
        "query_params": str(request.query_params),
        "user_agent": request.headers.get("User-Agent", ""),
        "x_forwarded_for": request.headers.get("X-Forwarded-For", ""),
    }

    try:
        sa = get_verified_identity(request)
        if sa:
            extra["service_account"] = sa
    except Exception:
        logger.warning("identity_verification_error", exc_info=True)

    audit_logger.warning("attestation_status_requested_deprecated", extra=extra)

    try:
        service = get_attestation_service()
        attested_nodes = service.list_attested_nodes()
        return JSONResponse(
            content={
                "attested_nodes": attested_nodes,
                "total_count": len(attested_nodes),
                "warning": "This endpoint is deprecated. Use /validate.",
                "deprecation": {
                    "sunset": _ATTEST_STATUS_KILL_DATE,
                    "link": _ATTEST_STATUS_SUNSET_LINK,
                    "migration": "/validate",
                },
            },
            headers={
                "Sunset": _ATTEST_STATUS_KILL_DATE,
                "Deprecation": "true",
                "Warning": (
                    '299 - "This endpoint is deprecated. '
                    "Use /validate. Sunset: "
                    + _ATTEST_STATUS_KILL_DATE
                    + ". See "
                    + _ATTEST_STATUS_SUNSET_LINK
                    + '"'
                ),
                "Link": "<" + _ATTEST_STATUS_SUNSET_LINK + '>; rel="sunset"',
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("attestation_status_failed", exc_info=exc)
        raise HTTPException(status_code=500, detail="Failed to get attestation status") from exc


async def handle_attest_node(request: Request):
    """Manually attest a node (for testing/admin purposes)."""
    from ..attestation_service import get_attestation_service

    try:
        data = await request.json()
        node_id = data.get("node_id")
        provider = data.get("provider", "tpm")
        attestation_data = data.get("attestation_data", {})

        if not node_id:
            audit_logger.warning("attest_node_missing_node_id")
            raise HTTPException(status_code=400, detail="node_id is required")

        audit_logger.info(
            "attest_node_attempt",
            extra={"node_id": node_id, "provider": provider},
        )

        service = get_attestation_service()
        result = service.attest_node(node_id, provider, attestation_data)

        if result.get("verified"):
            audit_logger.info(
                "attest_node_success",
                extra={"node_id": node_id, "provider": provider},
            )
        else:
            audit_logger.warning(
                "attest_node_failed",
                extra={
                    "node_id": node_id,
                    "provider": provider,
                    "error": result.get("error", "unknown"),
                },
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("attest_node_error", exc_info=e)
        audit_logger.warning(
            "attest_node_exception",
            extra={"error_type": type(e).__name__},
        )
        raise HTTPException(status_code=500, detail="Attestation failed") from e
