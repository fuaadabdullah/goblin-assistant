"""
Hardware-Backed Attestation Service
Verifies worker nodes are running on trusted hardware and approved configurations
"""

import os
import json
import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import redis
try:
    from google.cloud import compute_v1
except ImportError:
    compute_v1 = None  # GCP SDK optional

# Configure logging
logger = logging.getLogger(__name__)
audit_logger = logging.getLogger('attestation.audit')

# Input validation patterns
NODE_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,128}$')

# Boolean serialization sentinel values
VERIFIED_TRUE = "1"
VERIFIED_FALSE = "0"


@dataclass
class CachedAttestation:
    """Type-safe wrapper for cached attestation results from Redis.

    All fields are strings as returned from Redis, with explicit conversion
    for boolean values using sentinel constants ("1"/"0").
    """
    node_id: str
    verified: str  # "1" or "0"
    provider: str
    timestamp: str
    cache_until: str
    grace_period_until: str
    violations: Optional[str] = None  # JSON string or None
    error: Optional[str] = None
    measured_at: Optional[str] = None
    enclave_id: Optional[str] = None
    shielded_vm_enabled: Optional[str] = None
    integrity_monitoring_enabled: Optional[str] = None
    instance_id: Optional[str] = None

    @classmethod
    def from_redis_dict(cls, data: Dict[str, str]) -> 'CachedAttestation':
        """Convert Redis hash result to typed dataclass.

        Handles all fields being strings and uses sentinel values for bools.
        """
        return cls(
            node_id=data.get('node_id', ''),
            verified=data.get('verified', VERIFIED_FALSE),
            provider=data.get('provider', ''),
            timestamp=data.get('timestamp', ''),
            cache_until=data.get('cache_until', ''),
            grace_period_until=data.get('grace_period_until', ''),
            violations=data.get('violations'),
            error=data.get('error'),
            measured_at=data.get('measured_at'),
            enclave_id=data.get('enclave_id'),
            shielded_vm_enabled=data.get('shielded_vm_enabled'),
            integrity_monitoring_enabled=(
                data.get('integrity_monitoring_enabled')
            ),
            instance_id=data.get('instance_id'),
        )

    def to_redis_dict(self) -> Dict[str, str]:
        """Convert to Redis hash with all fields as strings."""
        result = {}
        for key, value in asdict(self).items():
            if value is not None:
                result[key] = str(value)
        return result


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
            # SECURITY: Check attestation freshness (reject replayed old docs)
            measured_at_str = attestation_data.get('measured_at')
            if measured_at_str:
                try:
                    measured_at = datetime.fromisoformat(measured_at_str)
                    age_seconds = (datetime.utcnow() - measured_at).total_seconds()
                    max_age_seconds = 5 * 60  # 5 minutes
                    if age_seconds > max_age_seconds:
                        audit_logger.warning(
                            "stale_attestation",
                            extra={
                                'node_id': node_id,
                                'provider': 'tpm',
                                'age_seconds': age_seconds
                            }
                        )
                        return {
                            'verified': False,
                            'provider': 'tpm',
                            'error': 'stale attestation document',
                            'node_id': node_id
                        }
                except (ValueError, TypeError):
                    logger.exception(
                        "invalid_measured_at_format",
                        extra={'node_id': node_id, 'measured_at': measured_at_str}
                    )
                    return {
                        'verified': False,
                        'provider': 'tpm',
                        'error': 'invalid measured_at timestamp',
                        'node_id': node_id
                    }

            # Check TPM PCR values
            pcr_values = attestation_data.get('pcr_values', {})
            expected_pcrs = self._get_expected_pcr_values()

            violations = []
            for pcr_index, expected_value in expected_pcrs.items():
                actual_value = pcr_values.get(f'pcr_{pcr_index}')
                if actual_value != expected_value:
                    violations.append(
                        f'PCR {pcr_index}: expected {expected_value}, '
                        f'got {actual_value}'
                    )

            is_verified = len(violations) == 0
            result = {
                'verified': is_verified,
                'provider': 'tpm',
                'violations': violations,
                'measured_at': attestation_data.get('measured_at'),
                'node_id': node_id
            }

            # Audit log the result
            if is_verified:
                audit_logger.info(
                    "attestation_verified",
                    extra={'node_id': node_id, 'provider': 'tpm'}
                )
            else:
                audit_logger.warning(
                    "attestation_failed",
                    extra={
                        'node_id': node_id,
                        'provider': 'tpm',
                        'violations': violations
                    }
                )

            return result

        except Exception as e:
            logger.exception(
                "tpm_verification_error",
                extra={'node_id': node_id, 'error': str(e)}
            )
            return {
                'verified': False,
                'provider': 'tpm',
                'error': str(e),
                'node_id': node_id
            }

    def _get_expected_pcr_values(self) -> Dict[int, str]:
        """Get expected PCR values for trusted boot chain
        
        SECURITY: All PCR values must be explicitly configured via environment variables.
        Refusing to start if any are missing — no hardcoded defaults accepted.
        """
        pcr_values = {}
        for pcr_index in [0, 1, 2]:
            env_key = f'TPM_PCR{pcr_index}_EXPECTED'
            pcr_val = os.environ.get(env_key)
            if not pcr_val:
                raise RuntimeError(
                    f"{env_key} must be set — refusing to start without "
                    "configured TPM PCR values"
                )
            pcr_values[pcr_index] = pcr_val
        return pcr_values

class GCPShieldedVMProvider(AttestationProvider):
    """Google Cloud Shielded VM attestation
    
    SECURITY: Verifies actual VM configuration against GCP Compute API,
    not client-supplied attestation_data. Prevents spoofing of Shielded VM status.
    
    Requires:
    - google-cloud-compute SDK installed
    - GCP credentials with compute.instances.get permissions
    - GCP_PROJECT_ID and GCP_ZONE environment variables (or configured at init)
    """

    def __init__(self, project_id: Optional[str] = None, zone: Optional[str] = None):
        self.project_id = project_id or os.getenv('GCP_PROJECT_ID')
        self.zone = zone or os.getenv('GCP_ZONE')
        self.compute_client = None
        
        # Lazy-load GCP client on first use (allows graceful degradation if SDK unavailable)
        if compute_v1:
            self.compute_client = compute_v1.InstancesClient()

    def verify_node(self, node_id: str, attestation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Verify Shielded VM by querying GCP Compute API
        
        SECURITY: Ignores client-supplied attestation_data. Fetches actual VM
        configuration from GCP and verifies shieldedInstanceConfig.
        """
        if not self.compute_client:
            return {
                'verified': False,
                'provider': 'gcp_shielded',
                'error': 'google-cloud-compute SDK not available',
                'node_id': node_id
            }
        
        if not self.project_id or not self.zone:
            return {
                'verified': False,
                'provider': 'gcp_shielded',
                'error': 'GCP_PROJECT_ID and GCP_ZONE must be configured',
                'node_id': node_id
            }
        
        try:
            # Fetch actual VM metadata from GCP API
            request = compute_v1.GetInstanceRequest(
                project=self.project_id,
                zone=self.zone,
                resource=node_id
            )
            instance = self.compute_client.get(request=request)
            
            # Check shieldedInstanceConfig from actual VM
            shielded_config = instance.shielded_instance_config
            if not shielded_config:
                return {
                    'verified': False,
                    'provider': 'gcp_shielded',
                    'shielded_vm_enabled': False,
                    'node_id': node_id,
                    'error': 'VM does not have shielded config'
                }
            
            # Verify both required security features are enabled
            is_shielded = shielded_config.enable_secure_boot or False
            integrity_enabled = shielded_config.enable_integrity_monitoring or False
            verified = is_shielded and integrity_enabled
            
            return {
                'verified': verified,
                'provider': 'gcp_shielded',
                'shielded_vm_enabled': is_shielded,
                'integrity_monitoring_enabled': integrity_enabled,
                'instance_id': instance.id,
                'node_id': node_id
            }

        except Exception as e:
            return {
                'verified': False,
                'provider': 'gcp_shielded',
                'error': f'GCP API verification failed: {str(e)}',
                'node_id': node_id
            }


class AWSNitroProvider(AttestationProvider):
    """AWS Nitro Enclave attestation"""

    def verify_node(self, node_id: str, attestation_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # SECURITY: Check attestation freshness (reject replayed old docs)
            attestation_doc = attestation_data.get('attestation_document', {})
            measured_at_str = attestation_doc.get('measured_at')
            if measured_at_str:
                try:
                    measured_at = datetime.fromisoformat(measured_at_str)
                    age_seconds = (datetime.utcnow() - measured_at).total_seconds()
                    max_age_seconds = 5 * 60  # 5 minutes
                    if age_seconds > max_age_seconds:
                        audit_logger.warning(
                            "stale_attestation",
                            extra={
                                'node_id': node_id,
                                'provider': 'aws_nitro',
                                'age_seconds': age_seconds
                            }
                        )
                        return {
                            'verified': False,
                            'provider': 'aws_nitro',
                            'error': 'stale attestation document',
                            'node_id': node_id
                        }
                except (ValueError, TypeError):
                    logger.exception(
                        "invalid_measured_at_format",
                        extra={'node_id': node_id, 'measured_at': measured_at_str}
                    )
                    return {
                        'verified': False,
                        'provider': 'aws_nitro',
                        'error': 'invalid measured_at timestamp',
                        'node_id': node_id
                    }

            # Verify Nitro attestation document
            pcr_values = attestation_doc.get('pcrs', {})

            # Verify against expected PCR values for Nitro
            expected_pcrs = self._get_nitro_expected_pcrs()
            violations = []

            for pcr_index, expected_value in expected_pcrs.items():
                actual_value = pcr_values.get(str(pcr_index))
                if actual_value != expected_value:
                    violations.append(
                        f'PCR {pcr_index}: expected {expected_value}, '
                        f'got {actual_value}'
                    )

            is_verified = len(violations) == 0
            result = {
                'verified': is_verified,
                'provider': 'aws_nitro',
                'violations': violations,
                'enclave_id': attestation_doc.get('enclave_id'),
                'node_id': node_id
            }

            # Audit log the result
            if is_verified:
                audit_logger.info(
                    "attestation_verified",
                    extra={'node_id': node_id, 'provider': 'aws_nitro'}
                )
            else:
                audit_logger.warning(
                    "attestation_failed",
                    extra={
                        'node_id': node_id,
                        'provider': 'aws_nitro',
                        'violations': violations
                    }
                )

            return result

        except Exception as e:
            logger.exception(
                "nitro_verification_error",
                extra={'node_id': node_id, 'error': str(e)}
            )
            return {
                'verified': False,
                'provider': 'aws_nitro',
                'error': str(e),
                'node_id': node_id
            }

    def _get_nitro_expected_pcrs(self) -> Dict[int, str]:
        """Get expected PCR values for AWS Nitro
        
        SECURITY: All PCR values must be explicitly configured via environment variables.
        Refusing to start if any are missing — no hardcoded defaults accepted.
        """
        pcr_values = {}
        for pcr_index in [0, 1, 2]:
            env_key = f'NITRO_PCR{pcr_index}'
            pcr_val = os.environ.get(env_key)
            if not pcr_val:
                raise RuntimeError(
                    f"{env_key} must be set — refusing to start without "
                    "configured Nitro PCR values"
                )
            pcr_values[pcr_index] = pcr_val
        return pcr_values

class AttestationService:
    """Main attestation service coordinating multiple providers
    
    SECURITY NOTES:
    - Validates all provider configurations at startup (fails loudly on misconfiguration)
    - Maintains a persistent revocation deny-list separate from cache
    - Uses cache_until (not grace_period_until) for validity checks
    - Grace period is reserved for future enhancement
    """
    
    # Redis key prefix for permanently revoked nodes (separate from cache)
    REVOKED_KEY_PREFIX = "attestation:revoked:"
    # Revocation TTL: 30 days (allows recovery from operator error, prevents unbounded growth)
    REVOCATION_TTL_SECONDS = 2592000

    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.redis_client: redis.Redis = redis.from_url(redis_url)

        # Attestation cache settings
        self.cache_ttl_seconds = int(
            os.getenv('ATTESTATION_CACHE_TTL', '3600')
        )  # 1 hour
        self.grace_period_seconds = int(
            os.getenv('ATTESTATION_GRACE_PERIOD', '300')
        )  # 5 min (reserved)

        # Initialize and validate attestation providers (fails on misconfiguration)
        self.providers = {}
        
        # Validate TPM provider configuration
        try:
            tpm_provider = TPMAttestationProvider()
            # Trigger validation by calling _get_expected_pcr_values
            tpm_provider._get_expected_pcr_values()
            self.providers['tpm'] = tpm_provider
        except RuntimeError as e:
            print(f"❌ TPM provider initialization failed: {e}")
            raise
        
        # Initialize GCP provider (validation deferred to first use)
        self.providers['gcp_shielded'] = GCPShieldedVMProvider()
        
        # Validate AWS Nitro provider configuration
        try:
            nitro_provider = AWSNitroProvider()
            # Trigger validation by calling _get_nitro_expected_pcrs
            nitro_provider._get_nitro_expected_pcrs()
            self.providers['aws_nitro'] = nitro_provider
        except RuntimeError as e:
            print(f"❌ AWS Nitro provider initialization failed: {e}")
            raise

    def attest_node(
        self, node_id: str, provider_type: str, attestation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform attestation for a node
        Returns attestation result with verification status

        SECURITY: Validates input, checks revocation deny-list before
        processing attestation request. Revoked nodes cannot re-attest
        until the deny-list expires (30 days).
        """
        try:
            # INPUT VALIDATION: Reject malformed node_id to prevent
            # Redis key injection attacks
            if not NODE_ID_PATTERN.match(node_id):
                audit_logger.warning(
                    "invalid_node_id",
                    extra={'node_id': node_id, 'provider': provider_type}
                )
                return {
                    'verified': False,
                    'error': 'invalid node_id format',
                    'node_id': node_id,
                    'timestamp': datetime.utcnow().isoformat()
                }

            # INPUT VALIDATION: Reject unknown provider types
            if provider_type not in self.providers:
                audit_logger.warning(
                    "unknown_provider",
                    extra={'node_id': node_id, 'provider': provider_type}
                )
                return {
                    'verified': False,
                    'error': f'unknown provider: {provider_type}',
                    'node_id': node_id,
                    'timestamp': datetime.utcnow().isoformat()
                }

            # REVOCATION CHECK: Block revoked nodes before any
            # other processing
            revoked_key = f"{self.REVOKED_KEY_PREFIX}{node_id}"
            if self.redis_client.exists(revoked_key):
                audit_logger.warning(
                    "revoked_node_attestation_attempt",
                    extra={'node_id': node_id, 'provider': provider_type}
                )
                return {
                    'verified': False,
                    'error': 'Node permanently revoked',
                    'node_id': node_id,
                    'timestamp': datetime.utcnow().isoformat()
                }

            # Check cache first
            cached_result = self._get_cached_attestation(node_id)
            if cached_result and self._is_cache_valid(cached_result):
                return cached_result

            # Get appropriate provider
            provider = self.providers.get(provider_type)

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
        """Check if a node has valid attestation.

        Uses cache_until (1 hour) as the validity window, NOT
        grace_period_until. Grace period is reserved for future
        enhancement (post-cache-expiry tolerance).
        """
        cached_result = self._get_cached_attestation(node_id)
        if not cached_result:
            return False

        # Use cache_until as the primary validity window (1 hour)
        try:
            cache_until_str = cached_result.get(
                'cache_until', '2000-01-01T00:00:00'
            )
            cache_until = datetime.fromisoformat(cache_until_str)
            is_not_expired = datetime.utcnow() <= cache_until
            # Use sentinel value "1" for verified (not string "True")
            is_verified = cached_result.get('verified') == VERIFIED_TRUE
            return is_not_expired and is_verified
        except (ValueError, TypeError):
            return False

    def get_node_attestation_status(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get current attestation status for a node"""
        return self._get_cached_attestation(node_id)

    def list_attested_nodes(self) -> List[Dict[str, Any]]:
        """List all currently attested nodes.

        SECURITY: Excludes permanently revoked nodes from the list.
        Uses non-blocking SCAN instead of KEYS to prevent Redis timeouts.
        """
        try:
            # Use SCAN instead of KEYS for non-blocking iteration
            attested_nodes = []
            cursor = 0
            pattern = "attestation:node:*"

            while True:
                cursor, batch_keys = self.redis_client.scan(
                    cursor, match=pattern, count=100
                )
                for key in batch_keys:
                    node_data = self.redis_client.hgetall(key)
                    if node_data:
                        node_info = {
                            k.decode('utf-8'): v.decode('utf-8')
                            for k, v in node_data.items()
                        }
                        attested_nodes.append(node_info)
                if cursor == 0:
                    break

            # Get set of revoked node IDs using SCAN (non-blocking)
            revoked_node_ids = set()
            revoked_pattern = f"{self.REVOKED_KEY_PREFIX}*"
            cursor = 0

            while True:
                cursor, batch_revoked = self.redis_client.scan(
                    cursor, match=revoked_pattern, count=100
                )
                for revoked_key in batch_revoked:
                    # Extract node_id from "attestation:revoked:node_id"
                    node_id = revoked_key.decode('utf-8').replace(
                        self.REVOKED_KEY_PREFIX, ''
                    )
                    revoked_node_ids.add(node_id)
                if cursor == 0:
                    break

            # Filter out revoked nodes
            result = [
                node for node in attested_nodes
                if node.get('node_id') not in revoked_node_ids
            ]
            return result

        except Exception as e:
            logger.exception(
                "list_attested_nodes_error",
                extra={'error': str(e)}
            )
            return []

    def revoke_node_attestation(self, node_id: str) -> bool:
        """Revoke attestation for a node (e.g., on compromise).

        SECURITY: Creates a permanent deny-list entry (separate from cache)
        that persists for 30 days. Revoked nodes cannot re-attest during
        this period, even if they pass verification. This prevents immediate
        re-attestation after compromise detection.

        Returns: True if revocation was successful (both cache deletion and
        deny-list creation)
        """
        try:
            # 1. Delete cached attestation result
            cache_key = f"attestation:node:{node_id}"
            cache_deleted = self.redis_client.delete(cache_key) > 0

            # 2. Add to permanent deny-list (survives cache expiry)
            revoked_key = f"{self.REVOKED_KEY_PREFIX}{node_id}"
            self.redis_client.set(
                revoked_key, "revoked", ex=self.REVOCATION_TTL_SECONDS
            )

            # Audit log the revocation
            audit_logger.warning(
                "node_revoked",
                extra={
                    'node_id': node_id,
                    'cache_deleted': cache_deleted,
                    'ttl_seconds': self.REVOCATION_TTL_SECONDS
                }
            )

            return True
        except Exception as e:
            logger.exception(
                "revocation_error",
                extra={'node_id': node_id, 'error': str(e)}
            )
            return False

    def _get_cached_attestation(
        self, node_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached attestation result from Redis."""
        try:
            key = f"attestation:node:{node_id}"
            data = self.redis_client.hgetall(key)

            if not data:
                return None

            return {
                k.decode('utf-8'): v.decode('utf-8')
                for k, v in data.items()
            }

        except Exception as e:
            logger.exception(
                "get_cached_attestation_error",
                extra={'node_id': node_id, 'error': str(e)}
            )
            return None

    def _cache_attestation_result(self, node_id: str, result: Dict[str, Any]):
        """Cache attestation result in Redis with proper serialization.

        Uses explicit "1"/"0" sentinel values for booleans to avoid
        case-sensitivity issues (e.g., "True" vs "true").
        """
        try:
            key = f"attestation:node:{node_id}"
            # Convert all values to strings for Redis, with explicit
            # sentinel values for booleans
            redis_data = {}
            for k, v in result.items():
                if v is True:
                    redis_data[k] = VERIFIED_TRUE
                elif v is False:
                    redis_data[k] = VERIFIED_FALSE
                else:
                    redis_data[k] = str(v)

            self.redis_client.hset(key, mapping=redis_data)
            self.redis_client.expire(key, self.cache_ttl_seconds)

        except Exception as e:
            logger.exception(
                "cache_attestation_result_error",
                extra={'node_id': node_id, 'error': str(e)}
            )

    def _is_cache_valid(self, cached_result: Dict[str, Any]) -> bool:
        """Check if cached attestation is still valid.

        Validates both expiration and verification status with detailed
        error handling for corrupted or missing cache data.
        Uses sentinel values "1"/"0" for boolean verification field.
        """
        if not cached_result or not isinstance(cached_result, dict):
            return False

        try:
            cache_until_str = cached_result.get(
                'cache_until', '2000-01-01T00:00:00'
            )
            if not isinstance(cache_until_str, str):
                return False

            cache_until = datetime.fromisoformat(cache_until_str)

            # Check expiration and verification status
            is_not_expired = datetime.utcnow() <= cache_until
            # Use sentinel value "1" for verified (not string "True")
            is_verified = cached_result.get('verified') == VERIFIED_TRUE

            return is_not_expired and is_verified

        except (ValueError, TypeError, AttributeError):
            # Invalid cache format - treat as expired
            return False
        except Exception:
            # Unexpected error - be conservative and invalidate cache
            return False



# Module-level singleton (lazy-initialized to avoid import-time Redis
# connection, enabling better testability and graceful fallback)
_attestation_service_instance: Optional[AttestationService] = None


def get_attestation_service() -> AttestationService:
    """Get or create the global AttestationService instance.

    Implements lazy singleton pattern: first call initializes the service,
    subsequent calls return the cached instance. This allows tests to reset
    the singleton via reset_attestation_service().
    """
    global _attestation_service_instance
    if _attestation_service_instance is None:
        _attestation_service_instance = AttestationService()
    return _attestation_service_instance


def reset_attestation_service() -> None:
    """Reset the global attestation service (for testing)."""
    global _attestation_service_instance
    _attestation_service_instance = None


# Kubernetes admission controller integration
def create_admission_webhook():
    """Create ValidatingWebhookConfiguration for Kubernetes admission control.

    This ensures only attested nodes can run sandbox workloads.

    SECURITY: Requires WEBHOOK_CA_BUNDLE environment variable to be set.
    Fails at runtime if missing to prevent deployment with insecure config.
    """
    # SECURITY: Validate CA bundle is configured before deployment
    ca_bundle = os.environ.get('WEBHOOK_CA_BUNDLE')
    if not ca_bundle:
        raise RuntimeError(
            "WEBHOOK_CA_BUNDLE environment variable must be set before "
            "deploying webhook (e.g., from cert-manager Secret)"
        )

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
                    "caBundle": ca_bundle
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



def get_attestation_status(node_id: str):
    """Get attestation status for a node."""
    service = get_attestation_service()
    status = service.get_node_attestation_status(node_id)
    if not status:
        return {"attested": False, "node_id": node_id}

    return {
        "attested": service.is_node_attested(node_id),
        "verified": status.get('verified') == VERIFIED_TRUE,
        "provider": status.get('provider'),
        "timestamp": status.get('timestamp'),
        "node_id": node_id
    }


def attest_node_endpoint(
    node_id: str, provider: str, attestation_data: Dict[str, Any]
):
    """Endpoint to attest a node."""
    service = get_attestation_service()
    result = service.attest_node(node_id, provider, attestation_data)
    return result


if __name__ == "__main__":
    # Test attestation service
    print("🛡️  Testing Attestation Service...")

    service = get_attestation_service()

    # Test TPM attestation
    test_data = {
        'pcr_values': {
            'pcr_0': 'trusted_boot_measurement',
            'pcr_1': 'kernel_measurement',
            'pcr_2': 'initramfs_measurement'
        },
        'measured_at': datetime.utcnow().isoformat()
    }

    result = service.attest_node('test-node-1', 'tpm', test_data)
    print(f"TPM Attestation Result: {result}")

    # Test attested status
    attested = service.is_node_attested('test-node-1')
    print(f"Node attested (expect True): {attested}")

    # Test negative case: unknown node should not be attested
    not_attested = service.is_node_attested('unknown-node')
    print(f"Unknown node attested (expect False): {not_attested}")

    # Test invalid node_id format
    invalid_result = service.attest_node(
        'invalid:node:id', 'tpm', test_data
    )
    print(f"Invalid node_id result: {invalid_result}")

    print("✅ Attestation service test complete")
