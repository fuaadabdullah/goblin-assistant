from __future__ import annotations

from api.services.agent_workflow import (
    ARCHITECT_MODEL,
    EDITOR_MODEL,
    build_agent_worker_payload,
    derive_workspace_contract,
)


def test_derive_workspace_contract_is_stable_for_repo_and_branch():
    workspace = derive_workspace_contract(
        repo_url="https://github.com/Acme/Goblin-Assistant.git",
        base_branch="main",
        task_id="task-123",
        branch_name="agent/add-rate-limiting",
    )

    assert workspace["workspace_id"] == "workspace-github-com-acme-goblin-assistant-main"
    assert workspace["workspace_family"] == "github.com/acme/goblin-assistant@main"
    assert workspace["sprite_name"] == "sprite-github-com-acme-goblin-assistant-main"
    assert workspace["persistent"] is True
    assert workspace["restore_policy"] == "restore-or-create"
    assert workspace["node_modules_cache"] is True
    assert workspace["venv_cache"] is True


def test_build_agent_worker_payload_uses_persistent_sprite_and_aider_split():
    payload = build_agent_worker_payload(
        task_id="task-123",
        task="add rate limiting",
        repo_url="https://github.com/acme/goblin-assistant",
        base_branch="main",
        branch_name="agent/add-rate-limiting",
        tests_command="pytest -q",
        source="ui",
        issue={"url": "https://github.com/acme/goblin-assistant/issues/42", "number": 42},
        metadata={"submitted_from": "web-agent-screen"},
        callback_url="http://127.0.0.1:8001/api/v1/agent/task/task-123/events",
        callback_secret="shared-secret",
    )

    assert payload["workspace"]["persistent"] is True
    assert payload["workspace"]["restore_policy"] == "restore-or-create"
    assert payload["workspace"]["sprite_provider"] == "fly.io"
    assert payload["worker_profile"]["architect_model"] == ARCHITECT_MODEL
    assert payload["worker_profile"]["editor_model"] == EDITOR_MODEL
    assert payload["worker_profile"]["aider_mode"] == "architect"
    assert payload["worker_profile"]["auto_commit_each_change"] is True
    assert payload["worker_profile"]["repair_attempts"] == 2
    assert payload["worker_profile"]["phase0_ci_commands"][0]["name"] == "pytest"
    assert payload["worker_profile"]["publish_strategy"] == "create-pull-request-only"
    assert payload["worker_profile"]["auto_merge"] is False
    assert payload["worker_profile"]["github_publish"]["library"] == "PyGithub"
    assert payload["worker_profile"]["github_publish"]["token_env"] == "GH_TOKEN"
    assert payload["worker_profile"]["isolation"]["hardware"] == "firecracker/kvm"
    assert payload["worker_profile"]["isolation"]["networking"] == "private-per-sandbox"
    assert payload["execution"]["persistent_sprite"] is True
    assert payload["execution"]["restore_or_create"] is True
    assert payload["execution"]["architect_model"] == ARCHITECT_MODEL
    assert payload["execution"]["editor_model"] == EDITOR_MODEL
    assert payload["execution"]["repair_attempts"] == 2
    assert payload["execution"]["ci_loop"]["max_repair_attempts"] == 2
    assert payload["execution"]["publish_strategy"] == "create-pull-request-only"
    assert payload["execution"]["auto_merge"] is False
    assert payload["execution"]["github_publish"]["method"] == "repo.create_pull"
    assert payload["callback_secret"] == "shared-secret"
