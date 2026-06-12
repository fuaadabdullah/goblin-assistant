"""Pydantic models for the Kubernetes Admission Webhook."""

from typing import Any, Dict

from pydantic import BaseModel


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
    Validate that the pod is scheduled on an attested node.
    Returns validation result.
    """
    from ..attestation_service import get_attestation_service

    node_name = extract_node_name_from_pod(pod_spec)

    if not node_name:
        return {
            "allowed": False,
            "message": "Pod does not specify nodeName - cannot validate attestation",
        }

    service = get_attestation_service()
    is_attested = service.is_node_attested(node_name)

    if is_attested:
        return {"allowed": True, "message": f"Node {node_name} has valid attestation"}
    return {
        "allowed": False,
        "message": f"Node {node_name} is not attested or attestation has expired",
    }
