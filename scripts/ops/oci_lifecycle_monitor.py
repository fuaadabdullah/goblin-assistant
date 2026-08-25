#!/usr/bin/env python3
"""OCI lifecycle monitor for the Goblin Assistant Oracle VM.

Tracks the instance and its runtime stack without relying on legacy idle
assumptions. Intended to run from cron or a systemd timer on the VM.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import ssl
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Iterable
from urllib.error import URLError
from urllib.request import Request, urlopen

IMDS_V2_VNICS_URL = "http://169.254.169.254/opc/v2/vnics/"
IMDS_V2_HEADERS = {"Authorization": "Bearer Oracle"}
DEFAULT_COMPOSE_SERVICES = ("api", "redis", "celery-worker", "caddy")
DEFAULT_API_URL = "http://127.0.0.1:8000/api/v1/health"
DEFAULT_WARN_DISK_PCT = 80.0
DEFAULT_WARN_MEMORY_PCT = 80.0
DEFAULT_WARN_SSL_DAYS = 14


@dataclass(frozen=True)
class Thresholds:
    disk_warn_pct: float = DEFAULT_WARN_DISK_PCT
    memory_warn_pct: float = DEFAULT_WARN_MEMORY_PCT
    ssl_warn_days: int = DEFAULT_WARN_SSL_DAYS


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _run(
    command: Iterable[str],
    *,
    cwd: Path | None = None,
    timeout: int = 15,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=str(cwd) if cwd is not None else None,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _load_json_from_command(command: Iterable[str], *, cwd: Path | None = None) -> Any | None:
    result = _run(command, cwd=cwd)
    if result.returncode != 0:
        return None
    payload = result.stdout.strip()
    if not payload:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None


def _resolve_api_url(domain: str | None, explicit_api_url: str | None) -> str:
    if explicit_api_url:
        return explicit_api_url
    if domain:
        return f"https://{domain.rstrip('/')}/api/v1/health"
    return DEFAULT_API_URL


def _fetch_public_ip() -> str | None:
    request = Request(IMDS_V2_VNICS_URL, headers=IMDS_V2_HEADERS)
    try:
        with urlopen(request, timeout=5) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None

    if isinstance(payload, dict):
        vnics = payload.get("data") if isinstance(payload.get("data"), list) else []
    else:
        vnics = payload if isinstance(payload, list) else []

    for vnic in vnics:
        if not isinstance(vnic, dict):
            continue
        for key in ("publicIp", "public-ip", "ip-address", "public_ip"):
            candidate = vnic.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    return None


def _check_vm_reachable(public_ip: str | None) -> Dict[str, Any]:
    reachable = bool(public_ip)
    status = "healthy" if reachable else "critical"
    return {
        "reachable": reachable,
        "public_ip": public_ip,
        "status": status,
        "source": "oci-imds",
    }


def _check_api_reachable(api_url: str) -> Dict[str, Any]:
    request = Request(api_url, headers={"User-Agent": "goblin-oci-lifecycle-monitor/1.0"})
    try:
        with urlopen(request, timeout=5) as response:  # noqa: S310
            status_code = getattr(response, "status", response.getcode())
            body = response.read().decode("utf-8", errors="replace")
        reachable = 200 <= int(status_code) < 300
        status = "healthy" if reachable else "critical"
        return {
            "reachable": reachable,
            "status": status,
            "status_code": int(status_code),
            "detail": body[:500],
            "url": api_url,
        }
    except URLError as exc:
        return {
            "reachable": False,
            "status": "critical",
            "error": str(exc),
            "url": api_url,
        }
    except Exception as exc:  # pragma: no cover - defensive
        return {
            "reachable": False,
            "status": "critical",
            "error": str(exc),
            "url": api_url,
        }


def _disk_utilization(path: Path = Path("/")) -> Dict[str, Any]:
    usage = os.statvfs(str(path))
    total = usage.f_frsize * usage.f_blocks
    free = usage.f_frsize * usage.f_bfree
    available = usage.f_frsize * usage.f_bavail
    used = total - free
    used_pct = (used / total * 100.0) if total else 0.0
    return {
        "path": str(path),
        "total_bytes": total,
        "used_bytes": used,
        "available_bytes": available,
        "used_percent": round(used_pct, 1),
    }


def _memory_utilization() -> Dict[str, Any]:
    meminfo: Dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if ":" not in line:
                continue
            key, raw_value = line.split(":", 1)
            value = raw_value.strip().split()[0]
            if value.isdigit():
                meminfo[key] = int(value) * 1024
    except FileNotFoundError:
        meminfo = {}

    total = meminfo.get("MemTotal", 0)
    available = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
    used = max(total - available, 0)
    used_pct = (used / total * 100.0) if total else 0.0
    return {
        "total_bytes": total,
        "used_bytes": used,
        "available_bytes": available,
        "used_percent": round(used_pct, 1),
    }


def _compose_services(compose_dir: Path) -> list[str]:
    result = _run(["docker", "compose", "config", "--services"], cwd=compose_dir)
    if result.returncode != 0:
        return list(DEFAULT_COMPOSE_SERVICES)
    services = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return services or list(DEFAULT_COMPOSE_SERVICES)


def _inspect_container(container_id: str) -> Dict[str, Any]:
    payload = _load_json_from_command(["docker", "inspect", container_id])
    if not isinstance(payload, list) or not payload:
        return {"status": "missing", "running": False}

    state = payload[0].get("State", {}) if isinstance(payload[0], dict) else {}
    health = state.get("Health", {}) if isinstance(state, dict) else {}
    status = ""
    if isinstance(health, dict):
        status = str(health.get("Status") or "").strip()
    if not status and isinstance(state, dict):
        status = str(state.get("Status") or "").strip()

    running = bool(state.get("Running")) if isinstance(state, dict) else False
    started_at = state.get("StartedAt") if isinstance(state, dict) else None
    finished_at = state.get("FinishedAt") if isinstance(state, dict) else None

    if running and status in {"", "running"}:
        status = "running"

    return {
        "status": status or "unknown",
        "running": running,
        "started_at": started_at,
        "finished_at": finished_at,
        "health": health.get("Status") if isinstance(health, dict) else None,
        "exit_code": state.get("ExitCode") if isinstance(state, dict) else None,
    }


def _container_health(compose_dir: Path, services: Iterable[str]) -> Dict[str, Any]:
    service_reports: Dict[str, Any] = {}
    overall = "healthy"

    for service in services:
        container_id_result = _run(["docker", "compose", "ps", "-q", service], cwd=compose_dir)
        container_id = container_id_result.stdout.strip() if container_id_result.returncode == 0 else ""
        if not container_id:
            service_reports[service] = {"status": "missing", "running": False}
            overall = "critical"
            continue

        report = _inspect_container(container_id)
        service_reports[service] = report

        status = str(report.get("status") or "").lower()
        if status in {"healthy", "running"}:
            continue
        if status in {"unhealthy", "exited", "dead", "missing"}:
            overall = "critical"
        else:
            if overall != "critical":
                overall = "degraded"

    return {"status": overall, "services": service_reports}


def _read_last_deployment(repo_root: Path) -> Dict[str, Any]:
    oracle_dir = repo_root / "infra" / "oracle"
    sha = _read_text(oracle_dir / ".last_deploy_sha")
    deployed_at = _read_text(oracle_dir / ".last_deploy_at")

    if not sha:
        result = _run(["git", "-C", str(repo_root), "rev-parse", "HEAD"])
        if result.returncode == 0:
            sha = result.stdout.strip() or None

    if not deployed_at:
        result = _run(["git", "-C", str(repo_root), "log", "-1", "--format=%cI"])
        if result.returncode == 0:
            deployed_at = result.stdout.strip() or None

    return {
        "commit_sha": sha,
        "deployed_at": deployed_at,
        "status": "healthy" if sha and deployed_at else "degraded",
        "source": "oracle-deploy-marker" if sha and deployed_at else "git-head",
    }


def _ssl_expiration(domain: str | None, thresholds: Thresholds) -> Dict[str, Any]:
    if not domain:
        return {
            "status": "unknown",
            "domain": None,
            "days_remaining": None,
            "expires_at": None,
        }

    context = ssl.create_default_context()
    try:
        with socket.create_connection((domain, 443), timeout=5) as raw_sock:
            with context.wrap_socket(raw_sock, server_hostname=domain) as tls_sock:
                cert = tls_sock.getpeercert()
    except Exception as exc:
        return {
            "status": "critical",
            "domain": domain,
            "error": str(exc),
            "days_remaining": None,
            "expires_at": None,
        }

    not_after = cert.get("notAfter") if isinstance(cert, dict) else None
    if not isinstance(not_after, str) or not not_after.strip():
        return {
            "status": "degraded",
            "domain": domain,
            "error": "certificate expiration missing",
            "days_remaining": None,
            "expires_at": None,
        }

    expires_at = datetime.fromtimestamp(ssl.cert_time_to_seconds(not_after), tz=UTC)
    delta = expires_at - datetime.now(UTC)
    days_remaining = int(delta.total_seconds() // 86400)
    if days_remaining < 0:
        status = "critical"
    elif days_remaining <= thresholds.ssl_warn_days:
        status = "degraded"
    else:
        status = "healthy"

    return {
        "status": status,
        "domain": domain,
        "expires_at": expires_at.isoformat(),
        "days_remaining": days_remaining,
    }


def _annotate_threshold_status(value: float, warn: float) -> str:
    if value >= 90.0:
        return "critical"
    if value >= warn:
        return "degraded"
    return "healthy"


def build_report(
    *,
    repo_root: Path,
    thresholds: Thresholds,
    domain: str | None = None,
    api_url: str | None = None,
    compose_dir: Path | None = None,
) -> Dict[str, Any]:
    compose_dir = compose_dir or (repo_root / "infra" / "oracle")
    resolved_api_url = _resolve_api_url(domain, api_url)
    public_ip = _fetch_public_ip()

    vm_reachable = _check_vm_reachable(public_ip)
    api_reachable = _check_api_reachable(resolved_api_url)
    disk_utilization = _disk_utilization()
    disk_utilization["status"] = _annotate_threshold_status(
        float(disk_utilization["used_percent"]), thresholds.disk_warn_pct
    )
    memory_utilization = _memory_utilization()
    memory_utilization["status"] = _annotate_threshold_status(
        float(memory_utilization["used_percent"]), thresholds.memory_warn_pct
    )
    container_health = _container_health(compose_dir, _compose_services(compose_dir))
    last_deployment = _read_last_deployment(repo_root)
    ssl_expiration = _ssl_expiration(domain, thresholds)

    issues: list[Dict[str, Any]] = []
    for label, component in (
        ("vm_reachable", vm_reachable),
        ("api_reachable", api_reachable),
        ("disk_utilization", disk_utilization),
        ("memory_utilization", memory_utilization),
        ("container_health", container_health),
        ("last_deployment", last_deployment),
        ("ssl_expiration", ssl_expiration),
    ):
        status = str(component.get("status") or "").lower()
        if status in {"critical", "degraded"}:
            issues.append({"component": label, "status": status, "detail": component})

    overall_status = "healthy" if not issues else "degraded"

    return {
        "status": overall_status,
        "timestamp": _utc_now(),
        "repo_root": str(repo_root),
        "api_url": resolved_api_url,
        "domain": domain,
        "public_ip": public_ip,
        "vm_reachable": vm_reachable,
        "api_reachable": api_reachable,
        "disk_utilization": disk_utilization,
        "memory_utilization": memory_utilization,
        "container_health": container_health,
        "last_deployment": last_deployment,
        "ssl_expiration": ssl_expiration,
        "issues": issues,
    }


def _render_text_report(report: Dict[str, Any]) -> str:
    lines = [
        f"OCI lifecycle monitor: {str(report['status']).upper()}",
        f"- VM reachable: {report['vm_reachable'].get('reachable')} "
        f"(public_ip={report.get('public_ip') or 'unknown'})",
        f"- API reachable: {report['api_reachable'].get('reachable')} "
        f"({report['api_reachable'].get('status_code', 'n/a')})",
        f"- Disk utilization: {report['disk_utilization'].get('used_percent')}% "
        f"({report['disk_utilization'].get('status')})",
        f"- Memory utilization: {report['memory_utilization'].get('used_percent')}% "
        f"({report['memory_utilization'].get('status')})",
        "- Container health: "
        + ", ".join(
            f"{name}={details.get('status')}"
            for name, details in report["container_health"]["services"].items()
        ),
        f"- Last deployment: {report['last_deployment'].get('deployed_at') or 'unknown'} "
        f"({report['last_deployment'].get('commit_sha') or 'unknown'})",
        f"- SSL expiration: {report['ssl_expiration'].get('expires_at') or 'unknown'} "
        f"({report['ssl_expiration'].get('days_remaining')} days remaining)",
    ]

    if report["issues"]:
        lines.append("- Issues:")
        for issue in report["issues"]:
            component = issue.get("component", "unknown")
            status = issue.get("status", "unknown")
            detail = issue.get("detail", {})
            lines.append(f"  - {component}: {status} -> {detail}")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Path to the goblin-assistant repository root.",
    )
    parser.add_argument(
        "--compose-dir",
        default="",
        help="Directory containing the Oracle docker-compose stack.",
    )
    parser.add_argument(
        "--domain",
        default=os.getenv("GOBLIN_API_DOMAIN", "").strip(),
        help="Public API domain used for SSL and external health checks.",
    )
    parser.add_argument(
        "--api-url",
        default=os.getenv("GOBLIN_API_URL", "").strip(),
        help="Override the API health URL.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    parser.add_argument(
        "--disk-warn-pct",
        type=float,
        default=float(os.getenv("OCI_MONITOR_DISK_WARN_PCT", DEFAULT_WARN_DISK_PCT)),
        help="Warn when disk utilization reaches this percentage.",
    )
    parser.add_argument(
        "--memory-warn-pct",
        type=float,
        default=float(os.getenv("OCI_MONITOR_MEMORY_WARN_PCT", DEFAULT_WARN_MEMORY_PCT)),
        help="Warn when memory utilization reaches this percentage.",
    )
    parser.add_argument(
        "--ssl-warn-days",
        type=int,
        default=int(os.getenv("OCI_MONITOR_SSL_WARN_DAYS", DEFAULT_WARN_SSL_DAYS)),
        help="Warn when SSL certificates expire within this many days.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    compose_dir = Path(args.compose_dir).resolve() if args.compose_dir else None
    thresholds = Thresholds(
        disk_warn_pct=args.disk_warn_pct,
        memory_warn_pct=args.memory_warn_pct,
        ssl_warn_days=args.ssl_warn_days,
    )
    report = build_report(
        repo_root=repo_root,
        thresholds=thresholds,
        domain=args.domain or None,
        api_url=args.api_url or None,
        compose_dir=compose_dir,
    )

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(_render_text_report(report))

    return 0 if report["status"] == "healthy" else 1


if __name__ == "__main__":
    raise SystemExit(main())
