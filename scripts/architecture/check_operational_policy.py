#!/usr/bin/env python3
"""Validate operational build, container, and deployment guardrails."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []

    dockerfile = _read("Dockerfile")
    compose = _read("docker-compose.yml")
    oracle_compose = _read("infra/oracle/docker-compose.yml")
    redis_conf = _read("redis.conf")
    deploy_prod = _read(".github/workflows/deploy-prod.yml")
    cloud_init = _read("infra/oracle/terraform/cloud-init.yml")
    outputs = _read("infra/oracle/terraform/outputs.tf")
    fly = _read("fly.toml")
    render = _read("render.yaml")
    oracle_env = _read("infra/oracle/.env.example")
    oracle_tf = _read("infra/oracle/terraform/main.tf")
    lifecycle_monitor = _read("scripts/ops/oci_lifecycle_monitor.py")
    storage_script_text = _read("infra/oracle/scripts/setup-persistent-storage.sh")
    storage_script = ROOT / "infra" / "oracle" / "scripts" / "setup-persistent-storage.sh"
    dependabot_path = ROOT / ".github" / "dependabot.yml"
    keepalive_script = ROOT / "scripts" / "supabase_keepalive.py"
    keepalive_workflow = ROOT / ".github" / "workflows" / "supabase-keepalive.yml"

    _require(
        "COPY . /app" not in dockerfile,
        "Dockerfile must not copy the whole repository into /app.",
        failures,
    )
    _require(
        "USER appuser" in dockerfile,
        "Dockerfile must switch to the non-root appuser runtime user.",
        failures,
    )
    _require(
        "COPY --chown=appuser:appuser apps/api/src" in dockerfile,
        "Dockerfile must selectively copy API runtime source.",
        failures,
    )
    _require(
        "PYTHONDONTWRITEBYTECODE=1" in dockerfile,
        "Dockerfile must avoid bytecode writes in read-only runtimes.",
        failures,
    )

    _require(
        "docker-socket-proxy:" in compose,
        "docker-compose.yml must route sandbox Docker API access through docker-socket-proxy.",
        failures,
    )
    _require(
        "DOCKER_HOST=tcp://docker-socket-proxy:2375" in compose,
        "sandbox-worker must use the bounded Docker socket proxy.",
        failures,
    )
    sandbox_section = compose.split("  sandbox-worker:", 1)[1].split("\n  #", 1)[0]
    _require(
        "/var/run/docker.sock" not in sandbox_section,
        "sandbox-worker must not mount /var/run/docker.sock directly.",
        failures,
    )
    _require(
        "read_only: true" in sandbox_section,
        "sandbox-worker must run with a read-only root filesystem.",
        failures,
    )
    _require(
        "./apps/api/src/api:/app/apps/api/src/api:ro" in compose,
        "API source bind mounts must be read-only and target the packaged source path.",
        failures,
    )

    _require(
        "ARCHIVED" in render
        and "Oracle Cloud (infra/oracle/) is the active deployment platform." in render,
        "render.yaml must remain archived while Oracle is the active deployment platform.",
        failures,
    )
    _require(
        "ARCHIVED" in fly
        and "Oracle Cloud (infra/oracle/) is the active deployment platform." in fly,
        "fly.toml must remain explicitly archived while Oracle is canonical.",
        failures,
    )
    _require(
        (ROOT / "infra" / "oracle" / "docker-compose.yml").exists(),
        "infra/oracle/docker-compose.yml must remain checked in for the Oracle runtime stack.",
        failures,
    )
    _require(
        (ROOT / "infra" / "oracle" / "terraform" / "main.tf").exists(),
        "infra/oracle/terraform/main.tf must remain checked in for Oracle provisioning.",
        failures,
    )
    _require(
        (ROOT / "infra" / "oracle" / "provision.sh").exists(),
        "infra/oracle/provision.sh must remain checked in for Oracle provisioning.",
        failures,
    )
    _require(
        storage_script.exists(),
        "infra/oracle/scripts/setup-persistent-storage.sh must remain checked in for Oracle persistent storage.",
        failures,
    )
    for token, message in (
        ("/opt/goblin/data", "infra/oracle/scripts/setup-persistent-storage.sh must mount the durable data volume at /opt/goblin/data."),
        ("/var/lib/docker", "infra/oracle/scripts/setup-persistent-storage.sh must bind Docker state onto the OCI volume."),
        ("/var/lib/redis", "infra/oracle/scripts/setup-persistent-storage.sh must bind Redis state onto the OCI volume."),
        ("/var/log/goblin", "infra/oracle/scripts/setup-persistent-storage.sh must bind Goblin logs onto the OCI volume."),
        ("$STORAGE_MOUNT_POINT/logs/goblin/api", "infra/oracle/scripts/setup-persistent-storage.sh must create the API log source path on the mounted OCI volume."),
        ("$STORAGE_MOUNT_POINT/logs/goblin/celery-worker", "infra/oracle/scripts/setup-persistent-storage.sh must create the Celery log source path on the mounted OCI volume."),
        ("/backups", "infra/oracle/scripts/setup-persistent-storage.sh must bind backups onto the OCI volume."),
    ):
        _require(token in storage_script_text, message, failures)
    _require(
        (ROOT / "infra" / "oracle" / "Caddyfile").exists(),
        "infra/oracle/Caddyfile must remain checked in for Oracle TLS routing.",
        failures,
    )
    _require(
        "profiles: [workers]" not in oracle_compose,
        "infra/oracle/docker-compose.yml must not hide the Celery worker behind a worker profile.",
        failures,
    )
    _require(
        "--concurrency=1" in oracle_compose,
        "infra/oracle/docker-compose.yml must keep the Celery worker at concurrency 1.",
        failures,
    )
    _require(
        "--workers 2" in oracle_compose,
        "infra/oracle/docker-compose.yml must cap the API at two Uvicorn workers.",
        failures,
    )
    _require(
        "REDIS_URL=redis://redis:6379/0" in oracle_compose,
        "infra/oracle/docker-compose.yml must run Redis locally on the OCI node.",
        failures,
    )
    _require(
        "/var/lib/redis:/data" in oracle_compose,
        "infra/oracle/docker-compose.yml must bind Redis data to /var/lib/redis on the OCI volume.",
        failures,
    )
    _require(
        "/opt/goblin/data/state/api:/app/state" in oracle_compose,
        "infra/oracle/docker-compose.yml must bind API state to /opt/goblin/data/state/api.",
        failures,
    )
    _require(
        "/var/log/goblin/api:/app/logs" in oracle_compose,
        "infra/oracle/docker-compose.yml must bind API logs to /var/log/goblin/api.",
        failures,
    )
    _require(
        "/var/log/goblin/celery-worker:/app/logs" in oracle_compose,
        "infra/oracle/docker-compose.yml must bind Celery worker logs to /var/log/goblin/celery-worker.",
        failures,
    )
    _require(
        "redis_data:" not in oracle_compose,
        "infra/oracle/docker-compose.yml must stop using a named Redis data volume.",
        failures,
    )
    _require(
        "api_state:" not in oracle_compose,
        "infra/oracle/docker-compose.yml must stop using a named API state volume.",
        failures,
    )
    _require(
        "api_logs:" not in oracle_compose,
        "infra/oracle/docker-compose.yml must stop using a named API logs volume.",
        failures,
    )
    _require(
        "maxmemory 384mb" in redis_conf,
        "redis.conf must cap Redis at 384mb so the OCI node retains memory headroom.",
        failures,
    )
    _require(
        "maxmemory-policy noeviction" in redis_conf,
        "redis.conf must use noeviction so Celery messages are not dropped under pressure.",
        failures,
    )
    _require(
        "celery-beat" not in oracle_compose,
        "infra/oracle/docker-compose.yml must not keep a separate Celery beat service on the tiny OCI node.",
        failures,
    )
    _require(
        "docker pull \"$GOBLIN_IMAGE\"" in deploy_prod
        and "docker pull \"$GOBLIN_SANDBOX_IMAGE\"" in deploy_prod
        and "docker compose up -d --no-build --remove-orphans" in deploy_prod,
        ".github/workflows/deploy-prod.yml must deploy the Oracle compose stack from pre-built images without building on the VM.",
        failures,
    )
    _require(
        "docker compose pull && docker compose up -d --no-build --remove-orphans" in cloud_init,
        "infra/oracle/terraform/cloud-init.yml must instruct operators to start the Oracle stack from pre-built images without building on the VM.",
        failures,
    )
    _require(
        "docker compose pull && docker compose up -d --no-build --remove-orphans" in outputs,
        "infra/oracle/terraform/outputs.tf must guide operators to start the Oracle stack from pre-built images without building on the VM.",
        failures,
    )
    _require(
        "REDIS_URL=redis://redis:6379/0" in oracle_env,
        "infra/oracle/.env.example must default Redis to the local OCI node.",
        failures,
    )
    _require(
        "bash /home/ubuntu/goblin-assistant/infra/oracle/scripts/setup-persistent-storage.sh" in cloud_init,
        "infra/oracle/terraform/cloud-init.yml must bootstrap the persistent storage layout before Docker starts.",
        failures,
    )
    _require(
        re.search(r'(?m)^\s*size_in_gbs\s*=\s*100\s*$', oracle_tf) is not None,
        "Oracle Terraform must provision a 100 GB data volume.",
        failures,
    )
    _require(
        "resource \"oci_core_volume\" \"goblin_data\"" in oracle_tf,
        "Oracle Terraform must define the persistent block volume resource.",
        failures,
    )
    _require(
        "resource \"oci_core_volume_attachment\" \"goblin_data\"" in oracle_tf,
        "Oracle Terraform must attach the persistent block volume to the instance.",
        failures,
    )
    _require(
        "resource \"oci_core_volume_backup_policy\" \"goblin_data\"" in oracle_tf,
        "Oracle Terraform must define a scheduled backup policy for the persistent block volume.",
        failures,
    )
    _require(
        "resource \"oci_core_volume_backup_policy_assignment\" \"goblin_data\"" in oracle_tf,
        "Oracle Terraform must assign the scheduled backup policy to the persistent block volume.",
        failures,
    )
    _require(
        re.search(r'(?m)^\s*backup_type\s*=\s*"INCREMENTAL"\s*$', oracle_tf) is not None
        and re.search(r'(?m)^\s*period\s*=\s*"ONE_DAY"\s*$', oracle_tf) is not None
        and re.search(r'(?m)^\s*retention_seconds\s*=\s*1209600\s*$', oracle_tf) is not None,
        "Oracle backup policy must schedule daily incremental backups with 14-day retention.",
        failures,
    )
    _require(
        re.search(r'(?m)^\s*attachment_type\s*=\s*"paravirtualized"\s*$', oracle_tf) is not None,
        "Oracle Terraform must use a paravirtualized block-volume attachment.",
        failures,
    )
    _require(
        re.search(r'(?m)^\s*is_consistent_volume_naming_enabled\s*=\s*true\s*$', oracle_tf) is not None,
        "Oracle Terraform must enable consistent volume naming for OCI block devices.",
        failures,
    )
    _require(
        re.search(r"(?m)^\s*ocpus\s*=\s*2\s*$", oracle_tf) is not None,
        "Oracle Terraform must target the Always Free 2 OCPU allocation.",
        failures,
    )
    _require(
        re.search(r"(?m)^\s*memory_in_gbs\s*=\s*12\s*$", oracle_tf) is not None,
        "Oracle Terraform must target the Always Free 12 GB allocation.",
        failures,
    )
    for token in (
        "vm_reachable",
        "api_reachable",
        "disk_utilization",
        "memory_utilization",
        "container_health",
        "last_deployment",
        "public_ip",
        "ssl_expiration",
    ):
        _require(
            token in lifecycle_monitor,
            f"scripts/ops/oci_lifecycle_monitor.py must track {token}.",
            failures,
        )
    _require(
        not keepalive_script.exists(),
        "scripts/supabase_keepalive.py must remain absent from the repo.",
        failures,
    )
    _require(
        not keepalive_workflow.exists(),
        ".github/workflows/supabase-keepalive.yml must remain absent from the repo.",
        failures,
    )

    _require(dependabot_path.exists(), "Dependabot configuration must exist.", failures)
    if dependabot_path.exists():
        dependabot = dependabot_path.read_text(encoding="utf-8")
        for ecosystem in ("pip", "npm", "github-actions"):
            _require(
                f"package-ecosystem: {ecosystem}" in dependabot,
                f"Dependabot must cover {ecosystem}.",
                failures,
            )

    if failures:
        print("Operational policy check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Operational policy check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
