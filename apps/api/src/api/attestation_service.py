"""Compatibility facade for attestation modules.

This module preserves the legacy import surface while delegating implementation
into the `api.attestation` package.
"""

from __future__ import annotations

import os
import importlib
from datetime import datetime
from typing import Any, Dict

from .attestation import providers as _providers
from .attestation.api import create_admission_webhook
from .attestation.models import (
    CachedAttestation,
    NODE_ID_PATTERN,
    VERIFIED_FALSE,
    VERIFIED_TRUE,
)
from .attestation.providers import AWSNitroProvider, AttestationProvider, TPMAttestationProvider
from .attestation.service import AttestationService
from .attestation.singleton import get_attestation_service, reset_attestation_service

# Backwards-compatible test patching surface.
import redis

_providers = importlib.reload(_providers)
compute_v1 = _providers.compute_v1


class GCPShieldedVMProvider(_providers.GCPShieldedVMProvider):
    """Compatibility wrapper preserving `module.compute_v1` patch behavior."""

    def __init__(self, project_id=None, zone=None):
        _providers.compute_v1 = compute_v1
        super().__init__(project_id=project_id, zone=zone)


def get_attestation_status(node_id: str):
    """Get attestation status for a node."""
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
    """Endpoint to attest a node."""
    service = get_attestation_service()
    return service.attest_node(node_id, provider, attestation_data)


if __name__ == "__main__":
    print("🛡️  Testing Attestation Service...")
    service = get_attestation_service()

    test_data = {
        "pcr_values": {
            "pcr_0": os.environ.get("TPM_PCR0_EXPECTED", "trusted_boot_measurement"),
            "pcr_1": os.environ.get("TPM_PCR1_EXPECTED", "kernel_measurement"),
            "pcr_2": os.environ.get("TPM_PCR2_EXPECTED", "initramfs_measurement"),
        },
        "measured_at": datetime.utcnow().isoformat(),
    }

    result = service.attest_node("test-node-1", "tpm", test_data)
    print(f"TPM Attestation Result: {result}")
    print(f"Node attested (expect True): {service.is_node_attested('test-node-1')}")
    print(f"Unknown node attested (expect False): {service.is_node_attested('unknown-node')}")

    invalid_result = service.attest_node("invalid:node:id", "tpm", test_data)
    print(f"Invalid node_id result: {invalid_result}")
    print("✅ Attestation service test complete")
