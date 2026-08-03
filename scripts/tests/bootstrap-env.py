#!/usr/bin/env python3
"""Bootstrap and audit local provider/auth secrets without printing values."""

from __future__ import annotations

import argparse
import getpass
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class SecretSpec:
    env_name: str
    vault_item: str
    label: str
    required: bool = False


PROVIDER_SECRETS = (
    SecretSpec("OPENAI_API_KEY", "goblin-dev-openai-key", "OpenAI API key"),
    SecretSpec("ANTHROPIC_API_KEY", "goblin-dev-anthropic-key", "Anthropic API key"),
    SecretSpec("GROQ_API_KEY", "goblin-dev-groq-key", "Groq API key"),
    SecretSpec(
        "SILICONEFLOW_API_KEY", "goblin-dev-siliconeflow-key", "SiliconeFlow API key"
    ),
    SecretSpec(
        "GOOGLE_AI_API_KEY", "goblin-dev-google-ai-key", "Google AI / Gemini API key"
    ),
    SecretSpec("DEEPSEEK_API_KEY", "goblin-dev-deepseek-key", "DeepSeek API key"),
    SecretSpec("TOGETHER_API_KEY", "goblin-dev-together-key", "Together AI API key"),
    SecretSpec(
        "HUGGINGFACE_API_KEY", "goblin-dev-huggingface-key", "Hugging Face API key"
    ),
    SecretSpec("COHERE_API_KEY", "goblin-dev-cohere-key", "Cohere API key"),
    SecretSpec(
        "DASHSCOPE_API_KEY", "goblin-dev-dashscope-key", "Aliyun DashScope API key"
    ),
    SecretSpec("AZURE_API_KEY", "goblin-dev-azure-key", "Azure OpenAI API key"),
    SecretSpec("ATLASSIAN_API_TOKEN", "goblin-dev-atlassian-token", "Atlassian token"),
)

INFRA_SECRETS = (
    SecretSpec(
        "JWT_SECRET_KEY",
        "goblin-dev-fastapi-secret",
        "FastAPI JWT signing secret",
        True,
    ),
    SecretSpec(
        "SUPABASE_URL", "goblin-prod-supabase-url", "Supabase project URL", True
    ),
    SecretSpec(
        "SUPABASE_ANON_KEY", "goblin-prod-supabase-anon-key", "Supabase anon key", True
    ),
    SecretSpec(
        "SUPABASE_SERVICE_ROLE_KEY",
        "goblin-prod-supabase-service-role-key",
        "Supabase service-role key",
    ),
    SecretSpec("SENTRY_DSN", "goblin-dev-sentry-dsn", "Sentry DSN"),
)

STALE_GCP_KEYS = (
    "OLLAMA_GCP_ENDPOINT",
    "OLLAMA_GCP_URL",
    "LLAMACPP_GCP_ENDPOINT",
    "LLAMACPP_GCP_URL",
    "GOOGLE_CLOUD_VLLM_ENDPOINT",
    "GOOGLE_CLOUD_VLLM_API_KEY",
)


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def is_configured(value: str | None) -> bool:
    if not value or not value.strip():
        return False
    normalized = value.strip().lower()
    placeholder_markers = (
        "your_",
        "your-",
        "replace-me",
        "changeme",
        "example.com",
        "<password>",
    )
    return not any(marker in normalized for marker in placeholder_markers)


def update_env_lines(lines: list[str], updates: dict[str, str]) -> list[str]:
    remaining = dict(updates)
    updated_lines: list[str] = []
    for line in lines:
        if "=" in line and not line.lstrip().startswith("#"):
            key = line.split("=", 1)[0].strip()
            if key in remaining:
                updated_lines.append(f"{key}={remaining.pop(key)}")
                continue
        updated_lines.append(line)
    if remaining:
        if updated_lines and updated_lines[-1].strip():
            updated_lines.append("")
        updated_lines.append("# Values written by scripts/bootstrap-env.py")
        updated_lines.extend(f"{key}={value}" for key, value in remaining.items())
    return updated_lines


def write_updates(
    path: Path, updates: dict[str, str], *, template: Path | None = None
) -> None:
    if not updates:
        return
    if not path.exists():
        initial = template.read_text(encoding="utf-8") if template else ""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(initial, encoding="utf-8")
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text(
        "\n".join(update_env_lines(lines, updates)) + "\n", encoding="utf-8"
    )


def unlock_bitwarden() -> str:
    if not shutil.which("bw"):
        raise RuntimeError(
            "Bitwarden CLI is not installed; install @bitwarden/cli first"
        )
    existing_session = os.getenv("BW_SESSION", "").strip()
    if existing_session:
        return existing_session
    result = subprocess.run(
        ["bw", "unlock", "--raw"], text=True, capture_output=True, check=False
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError("Unable to unlock the Bitwarden vault")
    return result.stdout.strip()


def read_bitwarden_secret(item_name: str, session: str) -> str:
    environment = os.environ.copy()
    environment["BW_SESSION"] = session
    for candidate in (item_name, item_name.replace("goblin-dev-", "goblin-prod-")):
        result = subprocess.run(
            ["bw", "get", "password", candidate],
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    return ""


def audit(specs: tuple[SecretSpec, ...], values: dict[str, str]) -> list[SecretSpec]:
    missing_required: list[SecretSpec] = []
    for spec in specs:
        configured = is_configured(
            os.getenv(spec.env_name) or values.get(spec.env_name)
        )
        priority = "required" if spec.required else "optional"
        print(f"  [{'ok' if configured else 'MISSING'}] {spec.label} ({priority})")
        if spec.required and not configured:
            missing_required.append(spec)
    return missing_required


def dogfood_provider_configured(values: dict[str, str]) -> bool:
    return any(
        is_configured(os.getenv(key) or values.get(key))
        for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY")
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bw", action="store_true", help="load values from Bitwarden")
    parser.add_argument("--check", action="store_true", help="audit only; do not write")
    parser.add_argument(
        "--env-file", default=".env", help="target env file relative to repo root"
    )
    parser.add_argument(
        "--web-env-file",
        default="apps/web/.env.local",
        help="target Next.js env file relative to repo root",
    )
    args = parser.parse_args()
    env_path = (REPO_ROOT / args.env_file).resolve()
    web_env_path = (REPO_ROOT / args.web_env_file).resolve()
    for option, path in (("--env-file", env_path), ("--web-env-file", web_env_path)):
        try:
            path.relative_to(REPO_ROOT)
        except ValueError:
            print(f"ERROR: {option} must stay inside the repository", file=sys.stderr)
            return 2

    current_values = parse_env_file(env_path)
    web_values = parse_env_file(web_env_path)
    all_specs = PROVIDER_SECRETS + INFRA_SECRETS
    if args.check:
        print(f"Auditing {env_path.name} (values are never displayed)")
        missing = audit(all_specs, current_values)
        if dogfood_provider_configured(current_values):
            print("  [ok] Dogfooding LLM provider (OpenAI or Anthropic)")
        else:
            print(
                "  [MISSING] Dogfooding LLM provider (OpenAI or Anthropic; one required)"
            )
        for key in STALE_GCP_KEYS:
            if is_configured(current_values.get(key)):
                print(f"  [STALE] {key} should be empty (GCP VM removed 2026-01-11)")
        frontend_missing = []
        for key in ("NEXT_PUBLIC_SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_ANON_KEY"):
            if is_configured(os.getenv(key) or web_values.get(key)):
                print(f"  [ok] {key} (required by the login UI)")
            else:
                print(f"  [MISSING] {key} (required by the login UI)")
                frontend_missing.append(key)
        if (
            missing
            or frontend_missing
            or not dogfood_provider_configured(current_values)
        ):
            missing_names = [spec.env_name for spec in missing]
            if not dogfood_provider_configured(current_values):
                missing_names.append("OPENAI_API_KEY|ANTHROPIC_API_KEY")
            missing_names.extend(frontend_missing)
            print("FAIL: missing required values: " + ", ".join(missing_names))
            return 1
        print("PASS: all required dogfooding values are configured")
        return 0

    session = ""
    if args.bw:
        try:
            session = unlock_bitwarden()
        except RuntimeError as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 1

    updates: dict[str, str] = {key: "" for key in STALE_GCP_KEYS}
    for spec in all_specs:
        existing = os.getenv(spec.env_name) or current_values.get(spec.env_name)
        if is_configured(existing):
            if not is_configured(current_values.get(spec.env_name)):
                updates[spec.env_name] = existing.strip()
                current_values[spec.env_name] = existing.strip()
                print(f"  [ok] {spec.label} copied from the process environment")
            else:
                print(f"  [ok] {spec.label} already configured")
            continue
        value = read_bitwarden_secret(spec.vault_item, session) if session else ""
        if not value and sys.stdin.isatty():
            value = getpass.getpass(
                f"  Enter {spec.label} ({'required' if spec.required else 'optional'}, Enter to skip): "
            ).strip()
        if "\n" in value or "\r" in value:
            print(f"ERROR: {spec.env_name} cannot contain a newline", file=sys.stderr)
            return 1
        if value:
            updates[spec.env_name] = value
            current_values[spec.env_name] = value
            print(f"  [ok] {spec.label} saved")
        else:
            print(f"  [skip] {spec.label}")

    write_updates(env_path, updates, template=REPO_ROOT / ".env.example")
    web_updates: dict[str, str] = {
        "BACKEND_URL": "http://127.0.0.1:8001",
        "NEXT_PUBLIC_BACKEND_URL": "http://127.0.0.1:8001",
    }
    public_supabase_values = {
        "NEXT_PUBLIC_SUPABASE_URL": os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        or current_values.get("SUPABASE_URL", ""),
        "NEXT_PUBLIC_SUPABASE_ANON_KEY": os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        or current_values.get("SUPABASE_ANON_KEY", ""),
    }
    web_updates.update(
        {
            key: value
            for key, value in public_supabase_values.items()
            if is_configured(value)
        }
    )
    write_updates(web_env_path, web_updates)
    missing = [
        spec
        for spec in all_specs
        if spec.required
        and not is_configured(
            os.getenv(spec.env_name) or current_values.get(spec.env_name)
        )
    ]
    missing_names = [spec.env_name for spec in missing]
    if not dogfood_provider_configured(current_values):
        missing_names.append("OPENAI_API_KEY|ANTHROPIC_API_KEY")
    missing_names.extend(
        key
        for key in ("NEXT_PUBLIC_SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_ANON_KEY")
        if not is_configured(public_supabase_values.get(key))
    )
    if missing_names:
        print("INCOMPLETE: missing required values: " + ", ".join(missing_names))
        return 1
    print(f"Bootstrap complete: {env_path} and {web_env_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
