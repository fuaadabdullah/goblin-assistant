"""Attestation API helpers and webhook config factory."""

from __future__ import annotations

import os
from typing import Any, Dict

from .models import VERIFIED_TRUE
from .singleton import get_attestation_service


def create_admission_webhook():
    ca_bundle = os.environ.get("WEBHOOK_CA_BUNDLE")
    if not ca_bundle:
        raise RuntimeError(
            "WEBHOOK_CA_BUNDLE environment variable must be set before deploying webhook (e.g., from cert-manager Secret)"
        )

    return {
        "apiVersion": "admissionregistration.k8s.io/v1",
        "kind": "ValidatingWebhookConfiguration",
        "metadata": {"name": "sandbox-attestation-webhook"},
        "webhooks": [
            {
                "name": "attestation-validator.sandbox.svc.cluster.local",
                "rules": [
                    {
                        "operations": ["CREATE", "UPDATE"],
                        "apiGroups": [""],
                        "apiVersions": ["v1"],
                        "resources": ["pods"],
                        "scope": "Namespaced",
                    }
                ],
                "clientConfig": {
                    "service": {
                        "name": "attestation-webhook",
                        "namespace": "sandbox",
                        "path": "/validate",
                    },
                    "caBundle": ca_bundle,
                },
                "admissionReviewVersions": ["v1", "v1beta1"],
                "sideEffects": "None",
                "timeoutSeconds": 5,
                "namespaceSelector": {"matchLabels": {"name": "sandbox"}},
                "objectSelector": {"matchLabels": {"app": "goblin-assistant-worker"}},
            }
        ],
    }


def get_attestation_status(node_id: str):
    service = get_attestation_service()
    status = service.get_node_attestation_status(node_id)
    if not status:
        return {"attested": False, "node_id": node_id}

    return {
        "attested": service.is_node_attested(node_id),
        "verified": status.get("verified") == VERIFIED_TRUE,
        "provider": status.get("provider"),
        "timestamp": status.get("timestamp"),
        "node_id": node_id,
    }


def attest_node_endpoint(node_id: str, provider: str, attestation_data: Dict[str, Any]):
    service = get_attestation_service()
    return service.attest_node(node_id, provider, attestation_data)
