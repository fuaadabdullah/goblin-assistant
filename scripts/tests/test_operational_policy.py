from __future__ import annotations

from pathlib import Path

import scripts.architecture.check_operational_policy as operational_policy


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _write_minimal_repo(root: Path, *, ocpus: int = 2, memory: int = 12) -> None:
    _write(
        root / "Dockerfile",
        "\n".join(
            [
                "FROM python:3.11-slim",
                "COPY --chown=appuser:appuser apps/api/src /app/apps/api/src",
                "ENV PYTHONDONTWRITEBYTECODE=1",
                "USER appuser",
                "",
            ]
        ),
    )
    _write(
        root / "docker-compose.yml",
        "\n".join(
            [
                "services:",
                "  sandbox-worker:",
                "    read_only: true",
                "    environment:",
                "      - DOCKER_HOST=tcp://docker-socket-proxy:2375",
                "    volumes:",
                "      - ./apps/api/src/api:/app/apps/api/src/api:ro",
                "  docker-socket-proxy:",
                "    image: tecnativa/docker-socket-proxy",
                "",
            ]
        ),
    )
    _write(
        root / "redis.conf",
        "\n".join(
            [
                "maxmemory 384mb",
                "maxmemory-policy noeviction",
                "",
            ]
        ),
    )
    archived_banner = (
        "# ARCHIVED — Oracle Cloud (infra/oracle/) is the active deployment platform.\n"
        "# This file is kept for reference only.\n"
    )
    _write(root / "render.yaml", archived_banner)
    _write(root / "fly.toml", archived_banner)
    _write(
        root / ".github" / "dependabot.yml",
        "\n".join(
            [
                "version: 2",
                "updates:",
                "  - package-ecosystem: pip",
                "    directory: \"/\"",
                "  - package-ecosystem: npm",
                "    directory: \"/\"",
                "  - package-ecosystem: github-actions",
                "    directory: \"/\"",
                "",
            ]
        ),
    )
    _write(
        root / ".github" / "workflows" / "deploy-prod.yml",
        "\n".join(
            [
                "name: Deploy to Production",
                "jobs:",
                "  deploy:",
                "    steps:",
                "      - run: |",
                "          docker pull \"$GOBLIN_IMAGE\"",
                "          docker pull \"$GOBLIN_SANDBOX_IMAGE\" || echo \"Sandbox image not yet built; skipping\"",
                "          docker compose up -d --no-build --remove-orphans",
                "",
            ]
        ),
    )
    _write(
        root / "infra" / "oracle" / "docker-compose.yml",
        "\n".join(
            [
                "services:",
                "  redis:",
                "    image: redis:7.2-alpine",
                "    command: redis-server /usr/local/etc/redis/redis.conf",
                "    environment:",
                "      - REDIS_URL=redis://redis:6379/0",
                "    volumes:",
                "      - /var/lib/redis:/data",
                "  api:",
                "    command: uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 2",
                "    environment:",
                "      - REDIS_URL=redis://redis:6379/0",
                "    volumes:",
                "      - /opt/goblin/data/state/api:/app/state",
                "      - /var/log/goblin/api:/app/logs",
                "  celery-worker:",
                "    command: >",
                "      celery -A celery_app:app worker",
                "      --loglevel=info",
                "      --concurrency=1",
                "    environment:",
                "      - REDIS_URL=redis://redis:6379/0",
                "    volumes:",
                "      - /var/log/goblin/celery-worker:/app/logs",
                "  caddy:",
                "    image: caddy:2-alpine",
                "",
            ]
        ),
    )
    _write(
        root / "infra" / "oracle" / ".env.example",
        "REDIS_URL=redis://redis:6379/0\n",
    )
    _write(
        root / "infra" / "oracle" / "terraform" / "cloud-init.yml",
        "\n".join(
            [
                "packages:",
                "  - e2fsprogs",
                "runcmd:",
                "  - bash /home/ubuntu/goblin-assistant/infra/oracle/scripts/setup-persistent-storage.sh",
                "  - docker compose pull && docker compose up -d --no-build --remove-orphans",
                "",
            ]
        ),
    )
    _write(
        root / "infra" / "oracle" / "terraform" / "outputs.tf",
        "docker compose pull && docker compose up -d --no-build --remove-orphans\n",
    )
    _write(root / "infra" / "oracle" / "provision.sh", "#!/usr/bin/env bash\n")
    _write(root / "infra" / "oracle" / "Caddyfile", "{\n}\n")
    _write(
        root / "infra" / "oracle" / "scripts" / "setup-persistent-storage.sh",
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "STORAGE_MOUNT_POINT=/opt/goblin/data",
                "/var/lib/docker",
                "/var/lib/redis",
                "/var/log/goblin",
                "$STORAGE_MOUNT_POINT/logs/goblin/api",
                "$STORAGE_MOUNT_POINT/logs/goblin/celery-worker",
                "/backups",
                "",
            ]
        ),
    )
    _write(
        root / "infra" / "oracle" / "terraform" / "main.tf",
        "\n".join(
            [
                "resource \"oci_core_volume\" \"goblin_data\" {",
                "  size_in_gbs = 100",
                "}",
                "",
                "resource \"oci_core_instance\" \"goblin\" {",
                "  shape = \"VM.Standard.A1.Flex\"",
                "  shape_config {",
                f"    ocpus         = {ocpus}",
                f"    memory_in_gbs = {memory}",
                "  }",
                "  launch_options {",
                "    is_consistent_volume_naming_enabled = true",
                "  }",
                "}",
                "",
                "resource \"oci_core_volume_attachment\" \"goblin_data\" {",
                "  attachment_type = \"paravirtualized\"",
                "}",
                "",
                "resource \"oci_core_volume_backup_policy\" \"goblin_data\" {",
                "  schedules {",
                "    backup_type                  = \"INCREMENTAL\"",
                "    period                       = \"ONE_DAY\"",
                "    retention_seconds            = 1209600",
                "  }",
                "}",
                "",
                "resource \"oci_core_volume_backup_policy_assignment\" \"goblin_data\" {",
                "  asset_id = oci_core_volume.goblin_data.id",
                "  policy_id = oci_core_volume_backup_policy.goblin_data.id",
                "}",
                "",
            ]
        ),
    )
    _write(
        root / "scripts" / "ops" / "oci_lifecycle_monitor.py",
        "\n".join(
            [
                "vm_reachable = True",
                "api_reachable = True",
                "disk_utilization = {}",
                "memory_utilization = {}",
                "container_health = {}",
                "last_deployment = {}",
                "public_ip = '203.0.113.10'",
                "ssl_expiration = {}",
                "",
            ]
        ),
    )


def test_operational_policy_passes_for_oracle_canonical_layout(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    _write_minimal_repo(root)
    monkeypatch.setattr(operational_policy, "ROOT", root)

    assert operational_policy.main() == 0


def test_operational_policy_rejects_old_oracle_shape(tmp_path, monkeypatch, capsys):
    root = tmp_path / "repo"
    _write_minimal_repo(root, ocpus=4, memory=24)
    monkeypatch.setattr(operational_policy, "ROOT", root)

    assert operational_policy.main() == 1
    output = capsys.readouterr().out
    assert "2 OCPU allocation" in output
    assert "12 GB allocation" in output
