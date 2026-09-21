from __future__ import annotations

from pathlib import Path

import scripts.ops.oci_lifecycle_monitor as monitor


def _healthy_report_stubs(monkeypatch) -> None:
    monkeypatch.setattr(monitor, "_fetch_public_ip", lambda: "203.0.113.10")
    monkeypatch.setattr(
        monitor,
        "_check_vm_reachable",
        lambda public_ip: {
            "reachable": True,
            "public_ip": public_ip,
            "status": "healthy",
            "source": "oci-imds",
        },
    )
    monkeypatch.setattr(
        monitor,
        "_check_api_reachable",
        lambda api_url: {
            "reachable": True,
            "status": "healthy",
            "status_code": 200,
            "detail": "ok",
            "url": api_url,
        },
    )
    monkeypatch.setattr(
        monitor,
        "_disk_utilization",
        lambda path=Path("/"): {
            "path": str(path),
            "total_bytes": 100,
            "used_bytes": 40,
            "available_bytes": 60,
            "used_percent": 40.0,
            "status": "healthy",
        },
    )
    monkeypatch.setattr(
        monitor,
        "_memory_utilization",
        lambda: {
            "total_bytes": 100,
            "used_bytes": 50,
            "available_bytes": 50,
            "used_percent": 50.0,
            "status": "healthy",
        },
    )
    monkeypatch.setattr(
        monitor,
        "_compose_services",
        lambda compose_dir: ["api", "redis", "celery-worker", "caddy"],
    )
    monkeypatch.setattr(
        monitor,
        "_container_health",
        lambda compose_dir, services: {
            "status": "healthy",
            "services": {
                service: {"status": "healthy", "running": True} for service in services
            },
        },
    )
    monkeypatch.setattr(
        monitor,
        "_read_last_deployment",
        lambda repo_root: {
            "commit_sha": "abc123",
            "deployed_at": "2026-08-19T12:00:00+00:00",
            "status": "healthy",
            "source": "oracle-deploy-marker",
        },
    )
    monkeypatch.setattr(
        monitor,
        "_ssl_expiration",
        lambda domain, thresholds: {
            "status": "healthy",
            "domain": domain,
            "expires_at": "2026-09-19T12:00:00+00:00",
            "days_remaining": 31,
        },
    )


def test_build_report_marks_healthy_stack(tmp_path, monkeypatch):
    _healthy_report_stubs(monkeypatch)
    repo_root = tmp_path / "repo"
    compose_dir = repo_root / "infra" / "oracle"
    compose_dir.mkdir(parents=True)

    report = monitor.build_report(
        repo_root=repo_root,
        thresholds=monitor.Thresholds(),
        domain="api.example.com",
        compose_dir=compose_dir,
    )

    assert report["status"] == "healthy"
    assert report["vm_reachable"]["reachable"] is True
    assert report["api_reachable"]["reachable"] is True
    assert report["container_health"]["status"] == "healthy"
    assert report["ssl_expiration"]["days_remaining"] == 31
    assert report["issues"] == []


def test_build_report_marks_degraded_when_ssl_is_close_to_expiry(tmp_path, monkeypatch):
    _healthy_report_stubs(monkeypatch)
    monkeypatch.setattr(
        monitor,
        "_ssl_expiration",
        lambda domain, thresholds: {
            "status": "critical",
            "domain": domain,
            "expires_at": "2026-08-01T12:00:00+00:00",
            "days_remaining": -18,
        },
    )

    repo_root = tmp_path / "repo"
    compose_dir = repo_root / "infra" / "oracle"
    compose_dir.mkdir(parents=True)

    report = monitor.build_report(
        repo_root=repo_root,
        thresholds=monitor.Thresholds(),
        domain="api.example.com",
        compose_dir=compose_dir,
    )

    assert report["status"] == "degraded"
    assert any(issue["component"] == "ssl_expiration" for issue in report["issues"])
