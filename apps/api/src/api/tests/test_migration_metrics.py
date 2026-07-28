from __future__ import annotations

from api.observability.migration_metrics import migration_metrics


def test_migration_metrics_records_provider_failure_rate():
    migration_metrics.reset_for_tests()
    migration_metrics.record_provider_probe(
        provider_id="openai",
        healthy=True,
        configured=True,
    )
    migration_metrics.record_provider_probe(
        provider_id="openai",
        healthy=False,
        configured=True,
    )
    migration_metrics.record_provider_probe(
        provider_id="unconfigured",
        healthy=False,
        configured=False,
    )

    snapshot = migration_metrics.snapshot()
    assert snapshot["provider_probe_totals"]["openai"] == 2
    assert snapshot["provider_probe_failures"]["openai"] == 1
    assert snapshot["provider_failure_rate"]["openai"] == 0.5
    assert "unconfigured" not in snapshot["provider_probe_totals"]


def test_migration_metrics_records_error_codes():
    migration_metrics.reset_for_tests()
    migration_metrics.record_error_code(
        lifecycle="legacy",
        error_code="SUPPORT_MESSAGE_REQUIRED",
        status_code=400,
    )
    snapshot = migration_metrics.snapshot()
    assert snapshot["error_code_totals"]["SUPPORT_MESSAGE_REQUIRED:400"] == 1
    assert snapshot["error_code_totals"]["lifecycle:legacy"] == 1
