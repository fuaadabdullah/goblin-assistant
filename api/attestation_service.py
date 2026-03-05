"""
Hardware-Backed Attestation Service
Verifies worker nodes are running on trusted hardware and approved configurations
"""

import os
import json
import time
import hashlib
import subprocess
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import redis

# Cloud provider attestation support
class AttestationProvider:
    """Base class for hardware attestation providers"""

    def verify_node(self, node_id: str, attestation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Verify node attestation. Returns verification result."""
        raise NotImplementedError

class TPMAttestationProvider(AttestationProvider):
    """TPM 2.0 hardware-backed attestation"""

    def verify_node(self, node_id: str, attestation_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Check TPM PCR values
            pcr_values = attestation_data.get('pcr_values', {})
            expected_pcrs = self._get_expected_pcr_values()

            violations = []
            for pcr_index, expected_value in expected_pcrs.items():
                actual_value = pcr_values.get(f'pcr_{pcr_index}')
                if actual_value != expected_value:
                    violations.append(f'PCR {pcr_index}: expected {expected_value}, got {actual_value}')

            return {
                'verified': len(violations) == 0,
                'provider': 'tpm',
                'violations': violations,
                'measured_at': attestation_data.get('measured_at'),
                'node_id': node_id
            }

        except Exception as e:
            return {
                'verified': False,
                'provider': 'tpm',
                'error': str(e),
                'node_id': node_id
            }

    def _get_expected_pcr_values(self) -> Dict[int, str]:
        """Get expected PCR values for trusted boot chain"""
        # In production, these would be securely stored and updated
        return {
            0: os.getenv('TPM_PCR0_EXPECTED', 'trusted_boot_measurement'),
            1: os.getenv('TPM_PCR1_EXPECTED', 'kernel_measurement'),
            2: os.getenv('TPM_PCR2_EXPECTED', 'initramfs_measurement'),
        }

class GCPShieldedVMProvider(AttestationProvider):
    """Google Cloud Shielded VM attestation"""

    def verify_node(self, node_id: str, attestation_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Verify Shielded VM integrity
            integrity_policy = attestation_data.get('integrity_policy', {})
            measurement = attestation_data.get('measurement')

            # Check if VM is shielded and integrity monitoring is enabled
            is_shielded = integrity_policy.get('shielded_vm', {}).get('enabled', False)
            integrity_enabled = integrity_policy.get('integrity_monitoring', {}).get('enabled', False)

            verified = is_shielded and integrity_enabled

            return {
                'verified': verified,
                'provider': 'gcp_shielded',
                'shielded_vm_enabled': is_shielded,
                'integrity_monitoring_enabled': integrity_enabled,
                'measurement': measurement,
                'node_id': node_id
            }

        except Exception as e:
            return {
                'verified': False,
                'provider': 'gcp_shielded',
                'error': str(e),
                'node_id': node_id
            }

class AWSNitroProvider(AttestationProvider):
    """AWS Nitro Enclave attestation"""

    def verify_node(self, node_id: str, attestation_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Verify Nitro attestation document
            attestation_doc = attestation_data.get('attestation_document', {})
            pcr_values = attestation_doc.get('pcrs', {})

            # Verify against expected PCR values for Nitro
            expected_pcrs = self._get_nitro_expected_pcrs()
            violations = []

            for pcr_index, expected_value in expected_pcrs.items():
                actual_value = pcr_values.get(str(pcr_index))
                if actual_value != expected_value:
                    violations.append(f'PCR {pcr_index}: expected {expected_value}, got {actual_value}')

            return {
                'verified': len(violations) == 0,
                'provider': 'aws_nitro',
                'violations': violations,
                'enclave_id': attestation_doc.get('enclave_id'),
                'node_id': node_id
            }

        except Exception as e:
            return {
                'verified': False,
                'provider': 'aws_nitro',
                'error': str(e),
                'node_id': node_id
            }

    def _get_nitro_expected_pcrs(self) -> Dict[int, str]:
        """Get expected PCR values for AWS Nitro"""
        return {
            0: os.getenv('NITRO_PCR0', 'nitro_boot_measurement'),
            1: os.getenv('NITRO_PCR1', 'kernel_measurement'),
            2: os.getenv('NITRO_PCR2', 'application_measurement'),
        }

class AttestationService:
    """Main attestation service coordinating multiple providers"""

    def __init__(self):
        self.redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))

        # Initialize attestation providers
        self.providers = {
            'tpm': TPMAttestationProvider(),
            'gcp_shielded': GCPShieldedVMProvider(),
            'aws_nitro': AWSNitroProvider(),
        }

        # Attestation cache settings
        self.cache_ttl_seconds = int(os.getenv('ATTESTATION_CACHE_TTL', '3600'))  # 1 hour
        self.grace_period_seconds = int(os.getenv('ATTESTATION_GRACE_PERIOD', '300'))  # 5 minutes

    def attest_node(self, node_id: str, provider_type: str, attestation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform attestation for a node
        Returns attestation result with verification status
        """
        try:
            # Check cache first
            cached_result = self._get_cached_attestation(node_id)
            if cached_result and self._is_cache_valid(cached_result):
                return cached_result

            # Get appropriate provider
            provider = self.providers.get(provider_type)
            if not provider:
                return {
                    'verified': False,
                    'error': f'Unsupported attestation provider: {provider_type}',
                    'node_id': node_id
                }

            # Perform attestation
            result = provider.verify_node(node_id, attestation_data)

            # Add metadata
            result.update({
                'timestamp': datetime.utcnow().isoformat(),
                'cache_until': (datetime.utcnow() + timedelta(seconds=self.cache_ttl_seconds)).isoformat(),
                'grace_period_until': (datetime.utcnow() + timedelta(seconds=self.grace_period_seconds)).isoformat(),
            })

            # Cache result
            self._cache_attestation_result(node_id, result)

            return result

        except Exception as e:
            return {
                'verified': False,
                'error': f'Attestation service error: {str(e)}',
                'node_id': node_id,
                'timestamp': datetime.utcnow().isoformat()
            }

    def is_node_attested(self, node_id: str) -> bool:
        """Check if a node has valid attestation (with grace period)"""
        cached_result = self._get_cached_attestation(node_id)
        if not cached_result:
            return False

        # Allow grace period for recently attested nodes
        grace_until = datetime.fromisoformat(cached_result.get('grace_period_until', '2000-01-01T00:00:00'))
        return datetime.utcnow() <= grace_until and cached_result.get('verified', False)

    def get_node_attestation_status(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get current attestation status for a node"""
        return self._get_cached_attestation(node_id)

    def list_attested_nodes(self) -> List[Dict[str, Any]]:
        """List all currently attested nodes"""
        try:
            pattern = "attestation:node:*"
            keys = self.redis_client.keys(pattern)

            attested_nodes = []
            for key in keys:
                node_data = self.redis_client.hgetall(key)
                if node_data:
                    node_info = {k.decode('utf-8'): v.decode('utf-8') for k, v in node_data.items()}
                    attested_nodes.append(node_info)

            return attested_nodes

        except Exception as e:
            print(f"❌ Error listing attested nodes: {e}")
            return []

    def revoke_node_attestation(self, node_id: str) -> bool:
        """Revoke attestation for a node (e.g., on compromise)"""
        try:
            key = f"attestation:node:{node_id}"
            result = self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            print(f"❌ Error revoking attestation for {node_id}: {e}")
            return False

    def _get_cached_attestation(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get cached attestation result"""
        try:
            key = f"attestation:node:{node_id}"
            data = self.redis_client.hgetall(key)

            if not data:
                return None

            return {k.decode('utf-8'): v.decode('utf-8') for k, v in data.items()}

        except Exception as e:
            print(f"❌ Error getting cached attestation: {e}")
            return None

    def _cache_attestation_result(self, node_id: str, result: Dict[str, Any]):
        """Cache attestation result"""
        try:
            key = f"attestation:node:{node_id}"
            # Convert all values to strings for Redis
            redis_data = {k: str(v) for k, v in result.items()}

            self.redis_client.hset(key, mapping=redis_data)
            self.redis_client.expire(key, self.cache_ttl_seconds)

        except Exception as e:
            print(f"❌ Error caching attestation result: {e}")

    def _is_cache_valid(self, cached_result: Dict[str, Any]) -> bool:
        """Check if cached attestation is still valid"""
        try:
            cache_until = datetime.fromisoformat(cached_result.get('cache_until', '2000-01-01T00:00:00'))
            return datetime.utcnow() <= cache_until and cached_result.get('verified', 'False') == 'True'
        except:
            return False

# Global attestation service instance
attestation_service = AttestationService()

# Kubernetes admission controller integration
def create_admission_webhook():
    """
    Create ValidatingWebhookConfiguration for Kubernetes admission control
    This ensures only attested nodes can run sandbox workloads
    """
    webhook_config = {
        "apiVersion": "admissionregistration.k8s.io/v1",
        "kind": "ValidatingWebhookConfiguration",
        "metadata": {
            "name": "sandbox-attestation-webhook"
        },
        "webhooks": [
            {
                "name": "attestation-validator.sandbox.svc.cluster.local",
                "rules": [
                    {
                        "operations": ["CREATE", "UPDATE"],
                        "apiGroups": [""],
                        "apiVersions": ["v1"],
                        "resources": ["pods"],
                        "scope": "Namespaced"
                    }
                ],
                "clientConfig": {
                    "service": {
                        "name": "attestation-webhook",
                        "namespace": "sandbox",
                        "path": "/validate"
                    },
                    "caBundle": ""  # Will be populated by cert-manager
                },
                "admissionReviewVersions": ["v1", "v1beta1"],
                "sideEffects": "None",
                "timeoutSeconds": 5,
                "namespaceSelector": {
                    "matchLabels": {
                        "name": "sandbox"
                    }
                },
                "objectSelector": {
                    "matchLabels": {
                        "app": "goblin-assistant-worker"
                    }
                }
            }
        ]
    }

    return webhook_config

# Node attestation API endpoints
def get_attestation_status(node_id: str):
    """Get attestation status for a node"""
    status = attestation_service.get_node_attestation_status(node_id)
    if not status:
        return {"attested": False, "node_id": node_id}

    return {
        "attested": attestation_service.is_node_attested(node_id),
        "verified": status.get('verified') == 'True',
        "provider": status.get('provider'),
        "timestamp": status.get('timestamp'),
        "node_id": node_id
    }

def attest_node_endpoint(node_id: str, provider: str, attestation_data: Dict[str, Any]):
    """Endpoint to attest a node"""
    result = attestation_service.attest_node(node_id, provider, attestation_data)
    return result

if __name__ == "__main__":
    # Test attestation service
    print("🛡️  Testing Attestation Service...")

    # Test TPM attestation
    test_data = {
        'pcr_values': {
            'pcr_0': 'trusted_boot_measurement',
            'pcr_1': 'kernel_measurement',
            'pcr_2': 'initramfs_measurement'
        },
        'measured_at': datetime.utcnow().isoformat()
    }

    result = attestation_service.attest_node('test-node-1', 'tpm', test_data)
    print(f"TPM Attestation Result: {result}")

    # Test attested status
    attested = attestation_service.is_node_attested('test-node-1')
    print(f"Node attested: {attested}")

    print("✅ Attestation service test complete")