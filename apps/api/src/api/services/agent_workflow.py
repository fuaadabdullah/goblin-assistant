"""Agent task workspace and worker contract helpers.

These helpers keep the route thin and make the persistent Sprite contract
testable without a live Fly.io deployment.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Mapping, Optional
from urllib.parse import urlparse

ARCHITECT_MODEL = "router-reason"
EDITOR_MODEL = "router-code"
SPRITE_PROVIDER = "fly.io"
DEFAULT_CHECKOUT_PATH = "/workspace/repo"
DEFAULT_WORKSPACE_RESTORE_POLICY = "restore-or-create"
DEFAULT_REPAIR_ATTEMPTS = 2
PHASE0_CI_COMMANDS = [
    {
        "name": "pytest",
        "command": 'cd apps/api && PYTHONPATH=src python3.11 -m pytest -o "addopts=" -v',
        "capture_output": True,
        "feed_failure_back_to_aider": True,
    },
    {
        "name": "lint",
        "command": "make lint",
        "capture_output": True,
        "feed_failure_back_to_aider": True,
    },
    {
        "name": "build",
        "command": "make build",
        "capture_output": True,
        "feed_failure_back_to_aider": True,
    },
]
GITHUB_TOKEN_ENV = "GH_TOKEN"
AGENT_PROMPT_BUDGET_ENV = "AGENT_PROMPT_TOKEN_BUDGET"
VERTEX_BATCH_MODE_ENV = "VERTEX_AGENT_BATCH_MODE"
VERTEX_CONTEXT_CACHING_ENV = "VERTEX_CONTEXT_CACHING_ENABLED"
VERTEX_CONTEXT_CACHE_ENV = "VERTEX_CONTEXT_CACHE_NAME"


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int = 0) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _slugify(value: str, fallback: str = "task") -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def _normalize_repo_slug(repo_url: str) -> str:
    candidate = repo_url.strip()
    if not candidate:
        return "repo/unknown"

    host = ""
    path = ""

    if candidate.startswith("git@") and ":" in candidate:
        prefix, remainder = candidate.split(":", 1)
        host = prefix.removeprefix("git@")
        path = remainder
    else:
        parsed = urlparse(candidate)
        host = parsed.netloc
        path = parsed.path
        if not host and parsed.path:
            parts = parsed.path.split("/", 1)
            if len(parts) == 2:
                host, path = parts[0], f"/{parts[1]}"

    host = host.strip().lower()
    path = path.strip().lstrip("/")
    if path.endswith(".git"):
        path = path[:-4]

    if host and path:
        return f"{host}/{path}".strip("/").lower()
    if path:
        return path.lower()
    return _slugify(candidate)


def derive_workspace_contract(
    *,
    repo_url: str,
    base_branch: str,
    task_id: str,
    branch_name: str,
    workspace_id: Optional[str] = None,
) -> Dict[str, Any]:
    repo_slug = _normalize_repo_slug(repo_url)
    normalized_base_branch = base_branch.strip() or "main"
    workspace_family = f"{repo_slug}@{normalized_base_branch}"
    stable_suffix = _slugify(workspace_family, fallback=task_id[:8] or "workspace")

    return {
        "workspace_id": workspace_id or f"workspace-{stable_suffix}",
        "workspace_family": workspace_family,
        "repo_slug": repo_slug,
        "sprite_name": f"sprite-{stable_suffix}",
        "checkout_ref": normalized_base_branch,
        "checkout_path": DEFAULT_CHECKOUT_PATH,
        "persistent": True,
        "restore_policy": DEFAULT_WORKSPACE_RESTORE_POLICY,
        "node_modules_cache": True,
        "venv_cache": True,
        "sprite_provider": SPRITE_PROVIDER,
        "branch_name": branch_name,
    }


def build_worker_profile(
    *,
    tests_command: str,
    base_branch: str,
    branch_name: str,
    repair_attempts: int,
) -> Dict[str, Any]:
    prompt_budget_tokens = _env_int(AGENT_PROMPT_BUDGET_ENV, 0)
    return {
        "kind": "sprite",
        "provider": SPRITE_PROVIDER,
        "isolation": {
            "hardware": "firecracker/kvm",
            "networking": "private-per-sandbox",
            "host_access": "blocked",
            "service_isolation": "blocked",
        },
        "architect_mode": "architect",
        "architect_model": ARCHITECT_MODEL,
        "editor_model": EDITOR_MODEL,
        "aider_mode": "architect",
        "auto_commit_each_change": True,
        "restore_policy": DEFAULT_WORKSPACE_RESTORE_POLICY,
        "repair_attempts": repair_attempts,
        "repair_strategy": "generate-test-repair",
        "phase0_ci_commands": PHASE0_CI_COMMANDS,
        "capture_ci_output": True,
        "publish_strategy": "create-pull-request-only",
        "auto_merge": False,
        "llm_optimization": {
            "prompt_budget_tokens": prompt_budget_tokens or None,
            "dashscope_short_request_budget": prompt_budget_tokens or None,
            "vertex_batch_mode": _env_flag(VERTEX_BATCH_MODE_ENV),
            "vertex_context_caching": _env_flag(VERTEX_CONTEXT_CACHING_ENV),
            "vertex_context_cache": os.getenv(VERTEX_CONTEXT_CACHE_ENV, "").strip() or None,
        },
        "github_publish": {
            "library": "PyGithub",
            "token_env": GITHUB_TOKEN_ENV,
            "method": "repo.create_pull",
            "create_pull_args": {
                "base": base_branch,
                "head": branch_name,
            },
            "merge_policy": "human_review_required",
        },
        "tests_command": tests_command,
        "base_branch": base_branch,
        "branch_name": branch_name,
    }


def build_agent_worker_payload(
    *,
    task_id: str,
    task: str,
    repo_url: str,
    base_branch: str,
    branch_name: str,
    tests_command: str,
    source: str,
    issue: Mapping[str, Any],
    metadata: Mapping[str, Any],
    callback_url: str,
    callback_secret: Optional[str],
    workspace: Optional[Mapping[str, Any]] = None,
    worker_profile: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    workspace_payload = dict(
        workspace
        or derive_workspace_contract(
            repo_url=repo_url,
            base_branch=base_branch,
            task_id=task_id,
            branch_name=branch_name,
        )
    )
    worker_profile_payload = dict(
        worker_profile
        or build_worker_profile(
            tests_command=tests_command,
            base_branch=base_branch,
            branch_name=branch_name,
            repair_attempts=DEFAULT_REPAIR_ATTEMPTS,
        )
    )

    return {
        "task_id": task_id,
        "task": task,
        "repo_url": repo_url,
        "base_branch": base_branch,
        "branch_name": branch_name,
        "tests_command": tests_command,
        "source": source,
        "issue": dict(issue),
        "metadata": dict(metadata),
        "workspace": workspace_payload,
        "worker_profile": worker_profile_payload,
        "callback_url": callback_url,
        "callback_secret": callback_secret or None,
        "execution": {
            "persistent_sprite": True,
            "restore_or_create": True,
            "auto_commit_each_change": True,
            "architect_model": ARCHITECT_MODEL,
            "editor_model": EDITOR_MODEL,
            "aider_mode": "architect",
            "tests_command": tests_command,
            "repair_attempts": worker_profile_payload.get(
                "repair_attempts", DEFAULT_REPAIR_ATTEMPTS
            ),
            "phase0_ci_commands": PHASE0_CI_COMMANDS,
            "capture_ci_output": True,
            "repair_strategy": "generate-test-repair",
            "publish_strategy": "create-pull-request-only",
            "auto_merge": False,
            "llm_optimization": worker_profile_payload.get("llm_optimization", {}),
            "github_publish": worker_profile_payload.get("github_publish", {}),
            "ci_loop": {
                "name": "phase0-ci",
                "commands": PHASE0_CI_COMMANDS,
                "capture_output": True,
                "max_repair_attempts": worker_profile_payload.get(
                    "repair_attempts", DEFAULT_REPAIR_ATTEMPTS
                ),
                "repair_instruction": "Feed the failing command output back to Aider and retry the edit loop.",
            },
            "isolation": worker_profile_payload.get("isolation", {}),
        },
    }


def resolve_default_repair_attempts() -> int:
    raw = os.getenv("AGENT_REPAIR_ATTEMPTS", str(DEFAULT_REPAIR_ATTEMPTS)).strip()
    try:
        attempts = int(raw)
    except ValueError:
        attempts = DEFAULT_REPAIR_ATTEMPTS
    return max(0, attempts)


def extract_contract_fields(task: Mapping[str, Any]) -> Dict[str, Any]:
    payload = task.get("payload") if isinstance(task.get("payload"), dict) else {}
    result = task.get("result") if isinstance(task.get("result"), dict) else {}
    workspace = {}
    worker_profile = {}
    if isinstance(payload.get("workspace"), dict):
        workspace = payload["workspace"]
    elif isinstance(result.get("workspace"), dict):
        workspace = result["workspace"]

    if isinstance(payload.get("worker_profile"), dict):
        worker_profile = payload["worker_profile"]
    elif isinstance(result.get("worker_profile"), dict):
        worker_profile = result["worker_profile"]

    return {
        "workspace_id": str(workspace.get("workspace_id") or result.get("workspace_id") or ""),
        "workspace_family": str(
            workspace.get("workspace_family") or result.get("workspace_family") or ""
        ),
        "sprite_name": str(workspace.get("sprite_name") or result.get("sprite_name") or ""),
        "checkout_ref": str(workspace.get("checkout_ref") or result.get("checkout_ref") or ""),
        "workspace_provider": str(
            workspace.get("sprite_provider") or result.get("workspace_provider") or SPRITE_PROVIDER
        ),
        "architect_model": str(
            worker_profile.get("architect_model")
            or result.get("architect_model")
            or ARCHITECT_MODEL
        ),
        "editor_model": str(
            worker_profile.get("editor_model") or result.get("editor_model") or EDITOR_MODEL
        ),
        "aider_mode": str(
            worker_profile.get("aider_mode") or result.get("aider_mode") or "architect"
        ),
        "auto_commit_each_change": bool(
            worker_profile.get("auto_commit_each_change")
            if "auto_commit_each_change" in worker_profile
            else result.get("auto_commit_each_change", True)
        ),
        "workspace": workspace,
        "worker_profile": worker_profile,
    }
