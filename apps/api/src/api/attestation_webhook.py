"""
Kubernetes Admission Controller for Hardware Attestation Validation
Ensures only attested nodes can run sandbox workloads
"""

import logging
import os
import time
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .attestation_service import get_attestation_service

# Configure logging
logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("attestation.webhook.audit")

app = FastAPI(title="Sandbox Attestation Webhook")


class AdmissionReview(BaseModel):
    """Kubernetes AdmissionReview request/response format"""

    apiVersion: str
    kind: str
    request: Dict[str, Any]


class AdmissionResponse(BaseModel):
    """Admission controller response"""

    apiVersion: str
    kind: str
    response: Dict[str, Any]


def extract_node_name_from_pod(pod_spec: Dict[str, Any]) -> str:
    """Extract node name from pod spec"""
    return pod_spec.get("spec", {}).get("nodeName", "")


def validate_pod_attestation(pod_spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that the pod is scheduled on an attested node
    Returns validation result
    """
    node_name = extract_node_name_from_pod(pod_spec)

    if not node_name:
        return {
            "allowed": False,
            "message": ("Pod does not specify nodeName - cannot validate attestation"),
        }

    # Check if node is attested
    service = get_attestation_service()
    is_attested = service.is_node_attested(node_name)

    if is_attested:
        return {"allowed": True, "message": f"Node {node_name} has valid attestation"}
    else:
        return {
            "allowed": False,
            "message": (f"Node {node_name} is not attested or attestation has expired"),
        }


def verify_service_account_token(
    token: str,
    audience: str = "attestation-webhook",
) -> Optional[str]:
    """Validate a Kubernetes ServiceAccount token using TokenReview.

    Returns the ServiceAccount username (e.g. "system:serviceaccount:ns:name")
    on success, otherwise None.
    """
    # Import kubernetes client/config lazily so module import doesn't fail
    try:
        from kubernetes import client, config  # type: ignore
    except ImportError:
        logger.debug("kubernetes client not available; skipping TokenReview")
        return None

    # Prefer catching kubernetes-specific config exceptions when possible
    ConfigException = getattr(config, "ConfigException", Exception)

    try:
        config.load_incluster_config()
    except ConfigException as exc:
        # not running in cluster; unit tests will mock TokenReview
        logger.debug("could not load in-cluster config", exc_info=exc)

    # Perform TokenReview
    # Use explicit attribute ignores where kubernetes stubs are incomplete
    auth_api = client.AuthenticationV1Api()  # type: ignore[attr-defined]
    spec = client.V1TokenReviewSpec(token=token, audiences=[audience])  # type: ignore[attr-defined]
    tr = client.V1TokenReview(spec=spec)  # type: ignore[attr-defined]

    # If kubernetes ApiException type is available, catch it explicitly
    k8s_client = client
    k8s_excs_mod = getattr(k8s_client, "exceptions", None)
    ApiException = getattr(k8s_excs_mod, "ApiException", None) if k8s_excs_mod else None

    if ApiException:
        try:
            resp = auth_api.create_token_review(body=tr)
        except ApiException as exc:
            logger.exception("token_review_api_exception", exc_info=exc)
            return None
    else:
        # No ApiException available in stubs; perform call and let other
        # unexpected exceptions propagate to the caller/test harness.
        resp = auth_api.create_token_review(body=tr)

    status = getattr(resp, "status", None)
    if not status or not getattr(status, "authenticated", False):
        return None
    user = getattr(status, "user", None)
    username = getattr(user, "username", None) if user else None
    return username


def get_verified_identity(request: Request) -> Optional[str]:
    """Get or compute the verified ServiceAccount identity for this request.

    Caches the result on request.state.service_account_username to avoid
    multiple TokenReview calls during a single request handling.
    """
    if hasattr(request.state, "service_account_username"):
        return request.state.service_account_username

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:]
    if not token:
        return None

    username = verify_service_account_token(token)
    # cache on request.state for reuse
    request.state.service_account_username = username
    return username


def rate_limit(
    limit_per_min: Optional[int] = None,
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """Simple Redis-backed fixed-window rate limiter decorator.

    Key is based on ServiceAccount username when available,
    otherwise remote IP.
    """

    def decorator(
        func: Callable[..., Awaitable[Any]],
    ) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(request: Request, *args: Any, **kwargs: Any) -> Any:
            # Determine key (prefer verified SA)
            sa = get_verified_identity(request)
            remote = None
            try:
                remote = request.client.host if request.client else None
            except AttributeError:
                # request.client may be missing in some test contexts
                remote = request.headers.get("X-Forwarded-For") or "unknown"

            key_id = sa or remote or "unknown"
            if limit_per_min is None:
                limit = int(os.getenv("ATTEST_NODE_RATE_LIMIT_PER_MIN", "60"))
            else:
                limit = int(limit_per_min)

            # Perform Redis-backed fixed-window counter. Catch Redis-specific
            # errors and allow requests to proceed if Redis is unavailable.
            try:
                import redis as _redis

                redis_client = get_attestation_service().redis_client
                now = int(time.time())
                window = now // 60
                key = f"attestation:ratelimit:{key_id}:{window}"
                try:
                    count = redis_client.incr(key)
                    if count == 1:
                        # First increment in this window - set expiry
                        redis_client.expire(key, 60)
                    if count > limit:
                        extra = {"key": key_id, "count": count}
                        audit_logger.warning(
                            "rate_limit_exceeded",
                            extra=extra,
                        )
                        raise HTTPException(
                            status_code=429,
                            detail="Rate limit exceeded",
                        )
                except _redis.RedisError as exc:
                    # Redis is down; log and allow request to proceed
                    logger.exception("rate_limit_redis_error", exc_info=exc)
            except (ImportError, AttributeError) as exc:
                # Redis not available or request.client missing in test envs
                logger.debug("rate_limit_unavailable", exc_info=exc)

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


def require_mtls(func):
    """Decorator to require mTLS (or proxy-forwarded client cert) for requests.

    Use SKIP_MTLS_CHECK=true in env for local development/testing.
    """

    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if os.getenv("SKIP_MTLS_CHECK", "false").lower() == "true":
            return await func(request, *args, **kwargs)

        # Common headers set by proxies that terminate TLS and
        # forward client cert info
        verify_header = request.headers.get("X-SSL-Client-Verify") or request.headers.get(
            "X-Client-Verify"
        )
        client_dn = request.headers.get("X-SSL-Client-S-DN") or request.headers.get(
            "X-SSL-CLIENT-S-DN"
        )

        if verify_header and verify_header.upper() == "SUCCESS":
            return await func(request, *args, **kwargs)

        # If we have a forwarded client DN, treat that as acceptable
        # only if coming from a trusted proxy
        if client_dn:
            # NOTE: Trust boundary must be enforced at proxy/network
            # level. We log and accept here
            logger.debug("client_dn_forwarded", extra={"dn": client_dn})
            return await func(request, *args, **kwargs)

        audit_logger.warning("mtls_missing", extra={"path": request.url.path})
        raise HTTPException(status_code=403, detail="mTLS required")

    return wrapper


@app.post("/validate")
@require_mtls
async def validate_admission(request: Request):
    """Admission controller webhook endpoint.

    SECURITY: Validates requests from Kubernetes API server via mTLS.
    Returns generic error messages to prevent information leakage.
    Logs all admission decisions for audit trail.
    """
    uid = "unknown"
    try:
        # Parse admission review
        body = await request.json()
        admission_review = AdmissionReview(**body)

        uid = admission_review.request.get("uid", "unknown")
        pod = admission_review.request.get("object", {})

        # Log admission review attempt
        pod_name = pod.get("metadata", {}).get("name", "unknown")
        namespace = pod.get("metadata", {}).get("namespace", "unknown")
        audit_logger.info(
            "admission_review_received",
            extra={"uid": uid, "pod": pod_name, "namespace": namespace},
        )

        # Validate pod attestation
        validation = validate_pod_attestation(pod)

        # Create admission response
        response = {
            "uid": uid,
            "allowed": validation["allowed"],
            "status": {"message": validation["message"]},
        }

        # If denied, provide warning
        if not validation["allowed"]:
            response["status"]["code"] = 403
            response["status"]["reason"] = "Forbidden"

            # Audit log denial
            audit_logger.warning(
                "admission_denied",
                extra={
                    "uid": uid,
                    "reason": validation["message"],
                    "pod": pod_name,
                    "namespace": namespace,
                },
            )

            # Create Kubernetes event for denied admission
            create_admission_denied_event(pod, validation["message"])
        else:
            # Audit log approval
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

    except (
        ValueError,
        TypeError,
        KeyError,
    ) as e:
        # Likely invalid payload or missing keys - deny admission securely
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


def create_admission_denied_event(pod: Dict[str, Any], reason: str):
    """Create a Kubernetes event for denied admission"""
    try:
        from kubernetes import client, config
    except ImportError as exc:
        logger.debug("kubernetes_client_unavailable", exc_info=exc)
        return

    # Load in-cluster config if available
    ConfigException = getattr(config, "ConfigException", Exception)
    try:
        config.load_incluster_config()
    except ConfigException as exc:
        logger.debug("could_not_load_incluster_config", exc_info=exc)

    v1 = client.CoreV1Api()

    # Extract pod information
    pod_name = pod.get("metadata", {}).get("name", "unknown")
    namespace = pod.get("metadata", {}).get("namespace", "sandbox")

    # Create event
    # Use a dynamic lookup to avoid static-checker false-positives on
    # kubernetes client attributes.
    kclient: Any = client  # type: ignore
    event_cls = getattr(kclient, "V1Event")  # type: ignore[attr-defined]
    event = event_cls(
        metadata=kclient.V1ObjectMeta(
            name=f"sandbox-attestation-denied-{pod_name}", namespace=namespace
        ),
        involved_object=kclient.V1ObjectReference(kind="Pod", name=pod_name, namespace=namespace),
        reason="AttestationValidationFailed",
        message=(f"Pod admission denied due to attestation failure: {reason}"),
        type="Warning",
        source=kclient.V1EventSource(component="sandbox-attestation-webhook"),
        first_timestamp=None,  # Set by Kubernetes
        last_timestamp=None,  # Set by Kubernetes
    )

    ApiException = getattr(
        getattr(client, "exceptions", None),
        "ApiException",
        None,
    )

    if ApiException:
        try:
            v1.create_namespaced_event(namespace, event)
        except ApiException as exc:
            logger.exception("create_namespaced_event_api_error", exc_info=exc)
    else:
        # If ApiException type is not available (stubs missing), attempt the
        # call and log any unexpected errors without failing admission flow.
        try:
            v1.create_namespaced_event(namespace, event)
        except Exception as exc:  # noqa: E722 - last-resort logging
            logger.exception(
                "create_admission_event_failed",
                extra={"error": str(exc)},
            )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Redis connectivity
        service = get_attestation_service()
        attested_count = len(service.list_attested_nodes())

        return {
            "status": "healthy",
            "attested_nodes": attested_count,
            "service": "attestation-webhook",
        }
    except Exception as exc:  # noqa: E722
        logger.exception("health_check_failed", exc_info=exc)
        raise HTTPException(status_code=503, detail="Health check failed") from exc


# Sunset date for /attestation-status — after this date the endpoint
# returns 410 Gone unless ATTEST_DEPRECATION_KILL_OVERRIDE is set.
_ATTEST_STATUS_KILL_DATE = "2026-08-25"
_ATTEST_STATUS_SUNSET_LINK = "https://docs.goblin.assistant/migration/attestation-validate"


@app.get("/attestation-status")
@rate_limit(limit_per_min=10)
async def get_attestation_status(request: Request):
    """DEPRECATED: Get current attestation status for all nodes.

    SECURITY: This endpoint is deprecated. Returns sensitive information
    about which nodes are attested. Use /validate instead.

    This endpoint is hard-deprecated:
      - Returns Sunset / Deprecation / Warning HTTP headers.
      - Rate limited to 10 requests/minute.
      - Logs every hit with full request metadata.
      - Will return 410 Gone after 2026-08-25 unless
        ATTEST_DEPRECATION_KILL_OVERRIDE=true is set.
    """
    # --- Kill-date guard ---
    kill_override = os.getenv("ATTEST_DEPRECATION_KILL_OVERRIDE", "").lower()
    if kill_override not in ("true", "1", "yes"):
        from datetime import date as _date

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
                detail=(
                    "This endpoint was deprecated and has been removed. Use /validate instead."
                ),
            )

    # --- Structured audit logging with full request metadata ---
    extra = {
        "path": request.url.path,
        "method": request.method,
        "client_host": (request.client.host if request.client else "unknown"),
        "query_params": str(request.query_params),
        "user_agent": request.headers.get("User-Agent", ""),
        "x_forwarded_for": request.headers.get("X-Forwarded-For", ""),
    }

    # Resolve service-account identity if available (do not reject on
    # missing auth — legacy clients may not send a token)
    try:
        sa = get_verified_identity(request)
        if sa:
            extra["service_account"] = sa
    except Exception:
        logger.warning("identity_verification_error", exc_info=True)

    audit_logger.warning(
        "attestation_status_requested_deprecated",
        extra=extra,
    )

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
                "Link": ("<" + _ATTEST_STATUS_SUNSET_LINK + '>; rel="sunset"'),
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("attestation_status_failed", exc_info=exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to get attestation status",
        ) from exc


def require_bearer_token(func):
    """Decorator to require Bearer token authentication.

    SECURITY: Validates Authorization header contains Bearer token.
    Returns 401 if missing or invalid.
    """

    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        auth_header = request.headers.get("Authorization", "")

        path = request.url.path

        if not auth_header.startswith("Bearer "):
            extra = {"path": path}
            audit_logger.warning("attest_node_missing_auth", extra=extra)
            raise HTTPException(status_code=401, detail="Authorization header required")

        token = auth_header[7:]
        if not token:
            extra = {"path": path}
            audit_logger.warning("attest_node_empty_token", extra=extra)
            raise HTTPException(status_code=401, detail="Authorization token required")

        # Validate token via TokenReview and cache identity on request.state
        sa_username = verify_service_account_token(token)
        if not sa_username:
            extra = {"path": path}
            audit_logger.warning("attest_node_invalid_token", extra=extra)
            raise HTTPException(status_code=401, detail="Invalid service account token")

        request.state.service_account_username = sa_username
        return await func(request, *args, **kwargs)

    return wrapper


@app.post("/attest-node")
@require_bearer_token
@rate_limit()
async def attest_node(request: Request):
    """Manually attest a node (for testing/admin purposes).

    SECURITY: Requires Bearer token (service account token).
    Authorization is validated via Kubernetes TokenReview.
    """
    try:
        data = await request.json()
        node_id = data.get("node_id")
        provider = data.get("provider", "tpm")
        attestation_data = data.get("attestation_data", {})

        if not node_id:
            audit_logger.warning("attest_node_missing_node_id")
            raise HTTPException(status_code=400, detail="node_id is required")

        # Log attestation attempt
        audit_logger.info(
            "attest_node_attempt",
            extra={"node_id": node_id, "provider": provider},
        )

        # Perform attestation
        service = get_attestation_service()
        result = service.attest_node(node_id, provider, attestation_data)

        # Log result
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
        audit_logger.warning("attest_node_exception", extra={"error_type": type(e).__name__})
        raise HTTPException(
            status_code=500,
            detail="Attestation failed",
        ) from e


if __name__ == "__main__":
    import uvicorn

    # For development/testing
    # SECURITY NOTE: Deploy with mTLS in production
    logger.info("Starting attestation webhook server on 0.0.0.0:8443")
    uvicorn.run("api.attestation_webhook:app", host="0.0.0.0", port=8443, reload=True)
