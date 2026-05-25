"""Attestation provider implementations."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

try:
    from google.cloud import compute_v1
except ImportError:
    compute_v1 = None

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("attestation.audit")


class AttestationProvider:
    """Base class for hardware attestation providers."""

    def verify_node(
        self, node_id: str, attestation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        raise NotImplementedError


class TPMAttestationProvider(AttestationProvider):
    """TPM 2.0 hardware-backed attestation."""

    def verify_node(
        self, node_id: str, attestation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            measured_at_str = attestation_data.get("measured_at")
            if measured_at_str:
                try:
                    measured_at = datetime.fromisoformat(measured_at_str)
                    age_seconds = (datetime.utcnow() - measured_at).total_seconds()
                    if age_seconds > 5 * 60:
                        audit_logger.warning(
                            "stale_attestation",
                            extra={
                                "node_id": node_id,
                                "provider": "tpm",
                                "age_seconds": age_seconds,
                            },
                        )
                        return {
                            "verified": False,
                            "provider": "tpm",
                            "error": "stale attestation document",
                            "node_id": node_id,
                        }
                except (ValueError, TypeError):
                    logger.exception(
                        "invalid_measured_at_format",
                        extra={"node_id": node_id, "measured_at": measured_at_str},
                    )
                    return {
                        "verified": False,
                        "provider": "tpm",
                        "error": "invalid measured_at timestamp",
                        "node_id": node_id,
                    }

            pcr_values = attestation_data.get("pcr_values", {})
            expected_pcrs = self._get_expected_pcr_values()
            violations = []

            for pcr_index, expected_value in expected_pcrs.items():
                actual_value = pcr_values.get(f"pcr_{pcr_index}")
                if actual_value != expected_value:
                    violations.append(
                        f"PCR {pcr_index}: expected {expected_value}, got {actual_value}"
                    )

            is_verified = len(violations) == 0
            result = {
                "verified": is_verified,
                "provider": "tpm",
                "violations": violations,
                "measured_at": attestation_data.get("measured_at"),
                "node_id": node_id,
            }

            if is_verified:
                audit_logger.info(
                    "attestation_verified",
                    extra={"node_id": node_id, "provider": "tpm"},
                )
            else:
                audit_logger.warning(
                    "attestation_failed",
                    extra={
                        "node_id": node_id,
                        "provider": "tpm",
                        "violations": violations,
                    },
                )

            return result

        except Exception as e:
            logger.exception(
                "tpm_verification_error", extra={"node_id": node_id, "error": str(e)}
            )
            return {
                "verified": False,
                "provider": "tpm",
                "error": str(e),
                "node_id": node_id,
            }

    def _get_expected_pcr_values(self) -> Dict[int, str]:
        pcr_values = {}
        for pcr_index in [0, 1, 2]:
            env_key = f"TPM_PCR{pcr_index}_EXPECTED"
            pcr_val = os.environ.get(env_key)
            if not pcr_val:
                raise RuntimeError(
                    f"{env_key} must be set — refusing to start without configured TPM PCR values"
                )
            pcr_values[pcr_index] = pcr_val
        return pcr_values


class GCPShieldedVMProvider(AttestationProvider):
    """Google Cloud Shielded VM attestation."""

    def __init__(self, project_id: Optional[str] = None, zone: Optional[str] = None):
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        self.zone = zone or os.getenv("GCP_ZONE")
        self.compute_client = None
        if compute_v1:
            self.compute_client = compute_v1.InstancesClient()

    def verify_node(
        self, node_id: str, attestation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not self.compute_client:
            return {
                "verified": False,
                "provider": "gcp_shielded",
                "error": "google-cloud-compute SDK not available",
                "node_id": node_id,
            }

        if not self.project_id or not self.zone:
            return {
                "verified": False,
                "provider": "gcp_shielded",
                "error": "GCP_PROJECT_ID and GCP_ZONE must be configured",
                "node_id": node_id,
            }

        try:
            request = compute_v1.GetInstanceRequest(
                project=self.project_id,
                zone=self.zone,
                resource=node_id,
            )
            instance = self.compute_client.get(request=request)
            shielded_config = instance.shielded_instance_config
            if not shielded_config:
                return {
                    "verified": False,
                    "provider": "gcp_shielded",
                    "shielded_vm_enabled": False,
                    "node_id": node_id,
                    "error": "VM does not have shielded config",
                }

            is_shielded = shielded_config.enable_secure_boot or False
            integrity_enabled = shielded_config.enable_integrity_monitoring or False
            verified = is_shielded and integrity_enabled
            return {
                "verified": verified,
                "provider": "gcp_shielded",
                "shielded_vm_enabled": is_shielded,
                "integrity_monitoring_enabled": integrity_enabled,
                "instance_id": instance.id,
                "node_id": node_id,
            }

        except Exception as e:
            return {
                "verified": False,
                "provider": "gcp_shielded",
                "error": f"GCP API verification failed: {str(e)}",
                "node_id": node_id,
            }


class AWSNitroProvider(AttestationProvider):
    """AWS Nitro Enclave attestation."""

    def verify_node(
        self, node_id: str, attestation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            attestation_doc = attestation_data.get("attestation_document", {})
            measured_at_str = attestation_doc.get("measured_at")
            if measured_at_str:
                try:
                    measured_at = datetime.fromisoformat(measured_at_str)
                    age_seconds = (datetime.utcnow() - measured_at).total_seconds()
                    if age_seconds > 5 * 60:
                        audit_logger.warning(
                            "stale_attestation",
                            extra={
                                "node_id": node_id,
                                "provider": "aws_nitro",
                                "age_seconds": age_seconds,
                            },
                        )
                        return {
                            "verified": False,
                            "provider": "aws_nitro",
                            "error": "stale attestation document",
                            "node_id": node_id,
                        }
                except (ValueError, TypeError):
                    logger.exception(
                        "invalid_measured_at_format",
                        extra={"node_id": node_id, "measured_at": measured_at_str},
                    )
                    return {
                        "verified": False,
                        "provider": "aws_nitro",
                        "error": "invalid measured_at timestamp",
                        "node_id": node_id,
                    }

            pcr_values = attestation_doc.get("pcrs", {})
            expected_pcrs = self._get_nitro_expected_pcrs()
            violations = []

            for pcr_index, expected_value in expected_pcrs.items():
                actual_value = pcr_values.get(str(pcr_index))
                if actual_value != expected_value:
                    violations.append(
                        f"PCR {pcr_index}: expected {expected_value}, got {actual_value}"
                    )

            is_verified = len(violations) == 0
            result = {
                "verified": is_verified,
                "provider": "aws_nitro",
                "violations": violations,
                "enclave_id": attestation_doc.get("enclave_id"),
                "node_id": node_id,
            }

            if is_verified:
                audit_logger.info(
                    "attestation_verified",
                    extra={"node_id": node_id, "provider": "aws_nitro"},
                )
            else:
                audit_logger.warning(
                    "attestation_failed",
                    extra={
                        "node_id": node_id,
                        "provider": "aws_nitro",
                        "violations": violations,
                    },
                )

            return result

        except Exception as e:
            logger.exception(
                "nitro_verification_error", extra={"node_id": node_id, "error": str(e)}
            )
            return {
                "verified": False,
                "provider": "aws_nitro",
                "error": str(e),
                "node_id": node_id,
            }

    def _get_nitro_expected_pcrs(self) -> Dict[int, str]:
        pcr_values = {}
        for pcr_index in [0, 1, 2]:
            env_key = f"NITRO_PCR{pcr_index}"
            pcr_val = os.environ.get(env_key)
            if not pcr_val:
                raise RuntimeError(
                    f"{env_key} must be set — refusing to start without configured Nitro PCR values"
                )
            pcr_values[pcr_index] = pcr_val
        return pcr_values
