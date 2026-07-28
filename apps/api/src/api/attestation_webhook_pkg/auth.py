"""Service account token verification for the attestation webhook."""

import logging
from typing import Optional

from fastapi import Request

logger = logging.getLogger(__name__)


def verify_service_account_token(
    token: str,
    audience: str = "attestation-webhook",
) -> Optional[str]:
    """Validate a Kubernetes ServiceAccount token using TokenReview.

    Returns the ServiceAccount username (e.g. "system:serviceaccount:ns:name")
    on success, otherwise None.
    """
    try:
        from kubernetes import client, config  # type: ignore
    except ImportError:
        logger.debug("kubernetes client not available; skipping TokenReview")
        return None

    ConfigException = getattr(config, "ConfigException", Exception)

    try:
        config.load_incluster_config()
    except ConfigException as exc:
        logger.debug("could not load in-cluster config", exc_info=exc)

    auth_api = client.AuthenticationV1Api()  # type: ignore[attr-defined]
    spec = client.V1TokenReviewSpec(token=token, audiences=[audience])  # type: ignore[attr-defined]
    tr = client.V1TokenReview(spec=spec)  # type: ignore[attr-defined]

    k8s_excs_mod = getattr(getattr(client, "exceptions", None), "ApiException", None)

    if k8s_excs_mod:
        try:
            resp = auth_api.create_token_review(body=tr)
        except k8s_excs_mod as exc:
            logger.exception("token_review_api_exception", exc_info=exc)
            return None
    else:
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
    request.state.service_account_username = username
    return username
