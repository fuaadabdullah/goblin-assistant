"""Attestation service orchestration and Redis-backed state."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import redis

from .models import NODE_ID_PATTERN, VERIFIED_FALSE, VERIFIED_TRUE
from .providers import (
    AWSNitroProvider,
    GCPShieldedVMProvider,
    TPMAttestationProvider,
)

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("attestation.audit")


class AttestationService:
    """Main attestation service coordinating multiple providers."""

    REVOKED_KEY_PREFIX = "attestation:revoked:"
    REVOCATION_TTL_SECONDS = 2592000

    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.redis_client: redis.Redis = redis.from_url(redis_url)

        self.cache_ttl_seconds = int(os.getenv("ATTESTATION_CACHE_TTL", "3600"))
        self.grace_period_seconds = int(os.getenv("ATTESTATION_GRACE_PERIOD", "300"))

        self.providers = {}

        try:
            tpm_provider = TPMAttestationProvider()
            tpm_provider._get_expected_pcr_values()
            self.providers["tpm"] = tpm_provider
        except RuntimeError as e:
            print(f"❌ TPM provider initialization failed: {e}")
            raise

        self.providers["gcp_shielded"] = GCPShieldedVMProvider()

        try:
            nitro_provider = AWSNitroProvider()
            nitro_provider._get_nitro_expected_pcrs()
            self.providers["aws_nitro"] = nitro_provider
        except RuntimeError as e:
            print(f"❌ AWS Nitro provider initialization failed: {e}")
            raise

    def attest_node(
        self, node_id: str, provider_type: str, attestation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            if not NODE_ID_PATTERN.match(node_id):
                audit_logger.warning(
                    "invalid_node_id",
                    extra={"node_id": node_id, "provider": provider_type},
                )
                return {
                    "verified": False,
                    "error": "invalid node_id format",
                    "node_id": node_id,
                    "timestamp": datetime.utcnow().isoformat(),
                }

            if provider_type not in self.providers:
                audit_logger.warning(
                    "unknown_provider",
                    extra={"node_id": node_id, "provider": provider_type},
                )
                return {
                    "verified": False,
                    "error": f"unknown provider: {provider_type}",
                    "node_id": node_id,
                    "timestamp": datetime.utcnow().isoformat(),
                }

            revoked_key = f"{self.REVOKED_KEY_PREFIX}{node_id}"
            if self.redis_client.exists(revoked_key):
                audit_logger.warning(
                    "revoked_node_attestation_attempt",
                    extra={"node_id": node_id, "provider": provider_type},
                )
                return {
                    "verified": False,
                    "error": "Node permanently revoked",
                    "node_id": node_id,
                    "timestamp": datetime.utcnow().isoformat(),
                }

            cached_result = self._get_cached_attestation(node_id)
            if cached_result and self._is_cache_valid(cached_result):
                return cached_result

            provider = self.providers.get(provider_type)
            result = provider.verify_node(node_id, attestation_data)
            result.update(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "cache_until": (
                        datetime.utcnow() + timedelta(seconds=self.cache_ttl_seconds)
                    ).isoformat(),
                    "grace_period_until": (
                        datetime.utcnow() + timedelta(seconds=self.grace_period_seconds)
                    ).isoformat(),
                }
            )
            self._cache_attestation_result(node_id, result)
            return result

        except Exception as e:
            return {
                "verified": False,
                "error": f"Attestation service error: {str(e)}",
                "node_id": node_id,
                "timestamp": datetime.utcnow().isoformat(),
            }

    def is_node_attested(self, node_id: str) -> bool:
        cached_result = self._get_cached_attestation(node_id)
        if not cached_result:
            return False

        try:
            cache_until_str = cached_result.get("cache_until", "2000-01-01T00:00:00")
            cache_until = datetime.fromisoformat(cache_until_str)
            is_not_expired = datetime.utcnow() <= cache_until
            is_verified = cached_result.get("verified") == VERIFIED_TRUE
            return is_not_expired and is_verified
        except (ValueError, TypeError):
            return False

    def get_node_attestation_status(self, node_id: str) -> Optional[Dict[str, Any]]:
        return self._get_cached_attestation(node_id)

    def list_attested_nodes(self) -> List[Dict[str, Any]]:
        try:
            attested_nodes = []
            cursor = 0
            pattern = "attestation:node:*"

            while True:
                cursor, batch_keys = self.redis_client.scan(cursor, match=pattern, count=100)
                for key in batch_keys:
                    node_data = self.redis_client.hgetall(key)
                    if node_data:
                        node_info = {
                            k.decode("utf-8"): v.decode("utf-8") for k, v in node_data.items()
                        }
                        attested_nodes.append(node_info)
                if cursor == 0:
                    break

            revoked_node_ids = set()
            revoked_pattern = f"{self.REVOKED_KEY_PREFIX}*"
            cursor = 0

            while True:
                cursor, batch_revoked = self.redis_client.scan(
                    cursor, match=revoked_pattern, count=100
                )
                for revoked_key in batch_revoked:
                    node_id = revoked_key.decode("utf-8").replace(self.REVOKED_KEY_PREFIX, "")
                    revoked_node_ids.add(node_id)
                if cursor == 0:
                    break

            return [node for node in attested_nodes if node.get("node_id") not in revoked_node_ids]

        except Exception as e:
            logger.exception("list_attested_nodes_error", extra={"error": str(e)})
            return []

    def revoke_node_attestation(self, node_id: str) -> bool:
        try:
            cache_key = f"attestation:node:{node_id}"
            cache_deleted = self.redis_client.delete(cache_key) > 0

            revoked_key = f"{self.REVOKED_KEY_PREFIX}{node_id}"
            self.redis_client.set(revoked_key, "revoked", ex=self.REVOCATION_TTL_SECONDS)

            audit_logger.warning(
                "node_revoked",
                extra={
                    "node_id": node_id,
                    "cache_deleted": cache_deleted,
                    "ttl_seconds": self.REVOCATION_TTL_SECONDS,
                },
            )

            return True
        except Exception as e:
            logger.exception("revocation_error", extra={"node_id": node_id, "error": str(e)})
            return False

    def _get_cached_attestation(self, node_id: str) -> Optional[Dict[str, Any]]:
        try:
            key = f"attestation:node:{node_id}"
            data = self.redis_client.hgetall(key)
            if not data:
                return None
            return {k.decode("utf-8"): v.decode("utf-8") for k, v in data.items()}
        except Exception as e:
            logger.exception(
                "get_cached_attestation_error",
                extra={"node_id": node_id, "error": str(e)},
            )
            return None

    def _cache_attestation_result(self, node_id: str, result: Dict[str, Any]):
        try:
            key = f"attestation:node:{node_id}"
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
                extra={"node_id": node_id, "error": str(e)},
            )

    def _is_cache_valid(self, cached_result: Dict[str, Any]) -> bool:
        if not cached_result or not isinstance(cached_result, dict):
            return False

        try:
            cache_until_str = cached_result.get("cache_until", "2000-01-01T00:00:00")
            if not isinstance(cache_until_str, str):
                return False

            cache_until = datetime.fromisoformat(cache_until_str)
            is_not_expired = datetime.utcnow() <= cache_until
            is_verified = cached_result.get("verified") == VERIFIED_TRUE
            return is_not_expired and is_verified

        except (ValueError, TypeError, AttributeError):
            return False
        except Exception:
            return False
