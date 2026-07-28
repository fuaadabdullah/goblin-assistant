#!/usr/bin/env python3
"""Validate operational build, container, and deployment guardrails."""

from __future__ import annotations

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
    fly = _read("fly.toml")
    dependabot_path = ROOT / ".github" / "dependabot.yml"

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
        (ROOT / "render.yaml").exists(),
        "render.yaml must remain the canonical backend deployment blueprint.",
        failures,
    )
    _require(
        "ARCHIVED" in fly
        and "Render (render.yaml) is the active deployment platform" in fly,
        "fly.toml must remain explicitly archived while Render is canonical.",
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
