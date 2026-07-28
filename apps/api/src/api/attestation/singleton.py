"""Lazy singleton helpers for AttestationService."""

from __future__ import annotations

from typing import Optional

from .service import AttestationService

_attestation_service_instance: Optional[AttestationService] = None


def get_attestation_service() -> AttestationService:
    global _attestation_service_instance
    if _attestation_service_instance is None:
        _attestation_service_instance = AttestationService()
    return _attestation_service_instance


def reset_attestation_service() -> None:
    global _attestation_service_instance
    _attestation_service_instance = None
