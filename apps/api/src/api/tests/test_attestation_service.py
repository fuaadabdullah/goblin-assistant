"""Tests for `api.attestation_service`.

These tests avoid real Redis and cloud SDK calls so they stay deterministic
while still covering the main attestation branches.
"""

from __future__ import annotations

import importlib
import sys
import types
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest


def _reload_attestation_service():
    import api.attestation_service as module

    return importlib.reload(module)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class FakeRedis:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}
        self.values: dict[str, str] = {}
        self.deleted_keys: list[str] = []
        self.expires: list[tuple[str, int]] = []
        self.set_calls: list[tuple[str, str, int | None]] = []

    def hset(self, key: str, mapping=None, **kwargs):
        payload = dict(mapping or {})
        payload.update(kwargs.get("mapping", {}))
        self.hashes[key] = payload
        return 1

    def hgetall(self, key: str):
        payload = self.hashes.get(key, {})
        return {k.encode("utf-8"): v.encode("utf-8") for k, v in payload.items()}

    def expire(self, key: str, ttl: int):
        self.expires.append((key, ttl))
        return True

    def exists(self, key: str):
        return key in self.values

    def delete(self, key: str):
        self.deleted_keys.append(key)
        removed = int(key in self.hashes)
        self.hashes.pop(key, None)
        self.values.pop(key, None)
        return removed

    def set(self, key: str, value: str, ex=None):
        self.values[key] = value
        self.set_calls.append((key, value, ex))
        return True

    def scan(self, _cursor, match=None, count=None, **_kwargs):
        if match == "attestation:node:*":
            keys = [k.encode("utf-8") for k in self.hashes.keys()]
            return 0, keys
        if match == "attestation:revoked:*":
            keys = [k.encode("utf-8") for k in self.values.keys()]
            return 0, keys
        return 0, []


def _apply_attestation_env(monkeypatch):
    monkeypatch.setenv("TPM_PCR0_EXPECTED", "pcr0")
    monkeypatch.setenv("TPM_PCR1_EXPECTED", "pcr1")
    monkeypatch.setenv("TPM_PCR2_EXPECTED", "pcr2")
    monkeypatch.setenv("NITRO_PCR0", "npcr0")
    monkeypatch.setenv("NITRO_PCR1", "npcr1")
    monkeypatch.setenv("NITRO_PCR2", "npcr2")
    monkeypatch.setenv("REDIS_URL", "redis://test/0")
    monkeypatch.setenv("ATTESTATION_CACHE_TTL", "3600")
    monkeypatch.setenv("ATTESTATION_GRACE_PERIOD", "300")
    monkeypatch.setenv("WEBHOOK_CA_BUNDLE", "ZmFrZS1jYS1idW5kbGU=")


@pytest.fixture
def api_attn_module(monkeypatch):
    _apply_attestation_env(monkeypatch)

    class FakeInstancesClient:
        def __init__(self):
            self.get = MagicMock()

    class FakeGetInstanceRequest:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    fake_compute_v1 = types.SimpleNamespace(
        InstancesClient=FakeInstancesClient,
        GetInstanceRequest=FakeGetInstanceRequest,
    )

    fake_google = types.SimpleNamespace(cloud=types.SimpleNamespace(compute_v1=fake_compute_v1))
    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.cloud", fake_google.cloud)
    monkeypatch.setitem(sys.modules, "google.cloud.compute_v1", fake_compute_v1)

    module = _reload_attestation_service()
    monkeypatch.setattr(module.redis, "from_url", lambda *_args, **_kwargs: FakeRedis())
    return module


@pytest.fixture
def api_attn_service(api_attn_module):
    return api_attn_module.AttestationService()


@pytest.fixture
def module_under_test(api_attn_module):
    return api_attn_module


@pytest.fixture
def service_under_test(api_attn_service):
    return api_attn_service


def test_cached_attestation_round_trip(module_under_test):
    cached = module_under_test.CachedAttestation(
        node_id="node-1",
        verified=module_under_test.VERIFIED_TRUE,
        provider="tpm",
        timestamp="2026-01-01T00:00:00",
        cache_until="2026-01-01T01:00:00",
        grace_period_until="2026-01-01T00:05:00",
        violations='["v1"]',
        error=None,
        measured_at="2026-01-01T00:00:00",
        enclave_id="enc-1",
        shielded_vm_enabled="true",
        integrity_monitoring_enabled="true",
        instance_id="instance-1",
    )

    redis_dict = cached.to_redis_dict()
    assert redis_dict["verified"] == module_under_test.VERIFIED_TRUE

    restored = module_under_test.CachedAttestation.from_redis_dict(redis_dict)
    assert restored == cached


def test_tpm_provider_verifies_expected_values(module_under_test):
    provider = module_under_test.TPMAttestationProvider()
    result = provider.verify_node(
        "node-1",
        {
            "pcr_values": {
                "pcr_0": "pcr0",
                "pcr_1": "pcr1",
                "pcr_2": "pcr2",
            },
            "measured_at": _now().isoformat(),
        },
    )

    assert result["verified"] is True
    assert result["provider"] == "tpm"
    assert result["node_id"] == "node-1"


def test_tpm_provider_rejects_stale_documents(module_under_test):
    provider = module_under_test.TPMAttestationProvider()
    stale_measured_at = (_now() - timedelta(minutes=6)).isoformat()

    result = provider.verify_node(
        "node-1",
        {"pcr_values": {}, "measured_at": stale_measured_at},
    )

    assert result["verified"] is False
    assert result["error"] == "stale attestation document"


def test_tpm_provider_rejects_invalid_measured_at(module_under_test):
    provider = module_under_test.TPMAttestationProvider()

    result = provider.verify_node(
        "node-1",
        {
            "pcr_values": {"pcr_0": "pcr0"},
            "measured_at": "not-a-timestamp",
        },
    )

    assert result["verified"] is False
    assert result["error"] == "invalid measured_at timestamp"


def test_aws_provider_verifies_expected_values(module_under_test):
    provider = module_under_test.AWSNitroProvider()
    result = provider.verify_node(
        "node-2",
        {
            "attestation_document": {
                "pcrs": {"0": "npcr0", "1": "npcr1", "2": "npcr2"},
                "enclave_id": "enc-2",
                "measured_at": _now().isoformat(),
            }
        },
    )

    assert result["verified"] is True
    assert result["provider"] == "aws_nitro"
    assert result["enclave_id"] == "enc-2"


def test_aws_provider_rejects_invalid_measured_at(module_under_test):
    provider = module_under_test.AWSNitroProvider()

    result = provider.verify_node(
        "node-2",
        {
            "attestation_document": {
                "pcrs": {"0": "npcr0"},
                "measured_at": "not-a-timestamp",
            }
        },
    )

    assert result["verified"] is False
    assert result["error"] == "invalid measured_at timestamp"


def test_gcp_provider_without_sdk_reports_unavailable(module_under_test):
    original_compute_v1 = module_under_test.compute_v1
    module_under_test.compute_v1 = None
    try:
        provider = module_under_test.GCPShieldedVMProvider()
        result = provider.verify_node("node-3", {})
    finally:
        module_under_test.compute_v1 = original_compute_v1

    assert result["verified"] is False
    assert result["error"] == "google-cloud-compute SDK not available"


def test_gcp_provider_requires_project_and_zone(module_under_test, monkeypatch):
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    monkeypatch.delenv("GCP_ZONE", raising=False)

    provider = module_under_test.GCPShieldedVMProvider()
    provider.compute_client = MagicMock()

    result = provider.verify_node("node-3", {})

    assert result["verified"] is False
    assert result["error"] == "GCP_PROJECT_ID and GCP_ZONE must be configured"


def test_gcp_provider_handles_instance_states(module_under_test):
    provider = module_under_test.GCPShieldedVMProvider(project_id="proj", zone="zone-a")
    provider.compute_client = MagicMock()

    provider.compute_client.get.return_value = types.SimpleNamespace(
        shielded_instance_config=None, id="instance-1"
    )
    missing = provider.verify_node("node-3", {})
    assert missing["error"] == "VM does not have shielded config"

    provider.compute_client.get.return_value = types.SimpleNamespace(
        shielded_instance_config=types.SimpleNamespace(
            enable_secure_boot=False,
            enable_integrity_monitoring=True,
        ),
        id="instance-2",
    )
    partial = provider.verify_node("node-3", {})
    assert partial["verified"] is False
    assert partial["shielded_vm_enabled"] is False
    assert partial["integrity_monitoring_enabled"] is True

    provider.compute_client.get.return_value = types.SimpleNamespace(
        shielded_instance_config=types.SimpleNamespace(
            enable_secure_boot=True,
            enable_integrity_monitoring=True,
        ),
        id="instance-3",
    )
    verified = provider.verify_node("node-3", {})
    assert verified["verified"] is True
    assert verified["instance_id"] == "instance-3"


def test_gcp_provider_handles_api_errors(module_under_test):
    provider = module_under_test.GCPShieldedVMProvider(project_id="proj", zone="zone-a")
    provider.compute_client = MagicMock()
    provider.compute_client.get.side_effect = RuntimeError("boom")

    result = provider.verify_node("node-3", {})

    assert result["verified"] is False
    assert result["error"].startswith("GCP API verification failed:")


def test_attestation_service_rejects_invalid_and_unknown_provider(
    service_under_test,
):
    invalid = service_under_test.attest_node("bad:node:id", "tpm", {"pcr_values": {}})
    assert invalid["verified"] is False
    assert invalid["error"] == "invalid node_id format"

    unknown = service_under_test.attest_node("node-1", "missing", {"pcr_values": {}})
    assert unknown["verified"] is False
    assert unknown["error"] == "unknown provider: missing"


def test_attestation_service_uses_cache_when_valid(service_under_test, module_under_test):
    service_under_test.redis_client.hashes["attestation:node:node-1"] = {
        "node_id": "node-1",
        "verified": module_under_test.VERIFIED_TRUE,
        "provider": "tpm",
        "timestamp": _now().isoformat(),
        "cache_until": (_now() + timedelta(minutes=30)).isoformat(),
        "grace_period_until": (_now() + timedelta(minutes=5)).isoformat(),
    }
    service_under_test.redis_client.expire("attestation:node:node-1", 3600)
    mock_verify_node = MagicMock()
    service_under_test.providers["tpm"].verify_node = mock_verify_node

    result = service_under_test.attest_node("node-1", "tpm", {"pcr_values": {}})

    assert result["node_id"] == "node-1"
    assert result["verified"] == module_under_test.VERIFIED_TRUE
    mock_verify_node.assert_not_called()


def test_attestation_service_caches_fresh_results(service_under_test, module_under_test):
    result = service_under_test.attest_node(
        "node-1",
        "tpm",
        {
            "pcr_values": {"pcr_0": "pcr0", "pcr_1": "pcr1", "pcr_2": "pcr2"},
            "measured_at": _now().isoformat(),
        },
    )

    assert result["verified"] is True
    assert result["cache_until"]
    assert result["grace_period_until"]
    assert (
        service_under_test.redis_client.hashes["attestation:node:node-1"]["verified"]
        == module_under_test.VERIFIED_TRUE
    )


def test_attestation_service_revocation_and_listing(
    service_under_test,
):
    service_under_test.attest_node(
        "node-1",
        "tpm",
        {
            "pcr_values": {"pcr_0": "pcr0", "pcr_1": "pcr1", "pcr_2": "pcr2"},
            "measured_at": _now().isoformat(),
        },
    )

    assert service_under_test.revoke_node_attestation("node-1") is True
    assert service_under_test.redis_client.deleted_keys[-1] == ("attestation:node:node-1")

    listed = service_under_test.list_attested_nodes()
    assert listed == []
    assert service_under_test.is_node_attested("node-1") is False


def test_attestation_service_rejects_revoked_node(service_under_test):
    service_under_test.attest_node(
        "node-9",
        "tpm",
        {
            "pcr_values": {"pcr_0": "pcr0", "pcr_1": "pcr1", "pcr_2": "pcr2"},
            "measured_at": _now().isoformat(),
        },
    )
    service_under_test.revoke_node_attestation("node-9")

    result = service_under_test.attest_node(
        "node-9",
        "tpm",
        {
            "pcr_values": {"pcr_0": "pcr0", "pcr_1": "pcr1", "pcr_2": "pcr2"},
            "measured_at": _now().isoformat(),
        },
    )

    assert result["error"] == "Node permanently revoked"


def test_attestation_service_handles_cache_helper_errors(
    service_under_test,
):
    service_under_test.redis_client.hgetall = MagicMock(side_effect=RuntimeError("redis boom"))
    service_under_test.redis_client.hset = MagicMock(side_effect=RuntimeError("redis boom"))

    assert service_under_test.get_node_attestation_status("node-x") is None
    assert service_under_test._get_cached_attestation("node-x") is None

    service_under_test._cache_attestation_result(
        "node-x",
        {
            "verified": True,
            "provider": "tpm",
            "timestamp": _now().isoformat(),
            "cache_until": _now().isoformat(),
            "grace_period_until": _now().isoformat(),
        },
    )


def test_attestation_service_cache_validation_edges(module_under_test):
    service = module_under_test.AttestationService()

    assert service._is_cache_valid(None) is False
    assert service._is_cache_valid({}) is False
    assert service._is_cache_valid({"verified": "0"}) is False
    assert service._is_cache_valid({"verified": "1", "cache_until": 123}) is False
    assert (
        service._is_cache_valid(
            {
                "verified": "1",
                "cache_until": (_now() + timedelta(minutes=5)).isoformat(),
            }
        )
        is True
    )


def test_attestation_service_singleton_helpers(module_under_test):
    module_under_test.reset_attestation_service()
    first = module_under_test.get_attestation_service()
    second = module_under_test.get_attestation_service()

    assert first is second


def test_attestation_helpers_and_webhook(module_under_test, service_under_test, monkeypatch):
    monkeypatch.setattr(
        module_under_test,
        "get_attestation_service",
        lambda: service_under_test,
    )

    status = module_under_test.get_attestation_status("missing-node")
    assert status == {"attested": False, "node_id": "missing-node"}

    webhook = module_under_test.create_admission_webhook()
    assert webhook["metadata"]["name"] == "sandbox-attestation-webhook"
    assert webhook["webhooks"][0]["clientConfig"]["caBundle"] == ("ZmFrZS1jYS1idW5kbGU=")


def test_create_admission_webhook_requires_ca_bundle(module_under_test, monkeypatch):
    monkeypatch.delenv("WEBHOOK_CA_BUNDLE", raising=False)
    with pytest.raises(RuntimeError, match="WEBHOOK_CA_BUNDLE"):
        module_under_test.create_admission_webhook()
