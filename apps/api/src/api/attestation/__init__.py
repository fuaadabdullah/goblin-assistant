"""Attestation package public API."""

from .api import attest_node_endpoint, create_admission_webhook, get_attestation_status
from .models import NODE_ID_PATTERN, VERIFIED_FALSE, VERIFIED_TRUE, CachedAttestation
from .providers import (
    AttestationProvider,
    AWSNitroProvider,
    GCPShieldedVMProvider,
    TPMAttestationProvider,
    compute_v1,
)
from .service import AttestationService
from .singleton import get_attestation_service, reset_attestation_service

__all__ = [
    "AWSNitroProvider",
    "AttestationProvider",
    "AttestationService",
    "CachedAttestation",
    "GCPShieldedVMProvider",
    "NODE_ID_PATTERN",
    "TPMAttestationProvider",
    "VERIFIED_FALSE",
    "VERIFIED_TRUE",
    "attest_node_endpoint",
    "compute_v1",
    "create_admission_webhook",
    "get_attestation_service",
    "get_attestation_status",
    "reset_attestation_service",
]
