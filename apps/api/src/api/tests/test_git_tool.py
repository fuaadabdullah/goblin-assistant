"""Tests for the git_tool skill."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from api.assistant_tools import git_tool  # noqa: F401 - triggers registration
from api.assistant_tools.registry import TOOL_REGISTRY


class TestGitToolRegistration:
    EXPECTED = {
        "git_status",
        "git_diff",
        "git_log",
        "git_add",
        "git_commit",
        "git_branch",
        "git_checkout",
        "git_pull",
        "git_push",
        "git_clone",
    }

    def test_git_tools_registered(self):
        assert self.EXPECTED.issubset(TOOL_REGISTRY.keys())

    def test_git_tools_have_git_category(self):
        for name in self.EXPECTED:
            assert TOOL_REGISTRY[name].category == "git"


def _init_git_repo(path: Path) -> Path:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True, text=True)
    (path / "README.md").write_text("hello", encoding="utf-8")
    return path


class TestGitStatus:
    @pytest.mark.asyncio
    async def test_status_succeeds_in_real_repo(self, tmp_path):
        repo = _init_git_repo(tmp_path)

        result = await TOOL_REGISTRY["git_status"].handler(repo_path=str(repo))

        assert result["returncode"] == 0
        assert result["repo"] == str(repo)
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_missing_repo_path_returns_error(self, tmp_path):
        missing = tmp_path / "missing"

        result = await TOOL_REGISTRY["git_status"].handler(repo_path=str(missing))

        assert "error" in result
        assert "does not exist" in result["error"].lower()


class TestGitPushFailures:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("stderr", "expected"),
        [
            ("fatal: Authentication failed", "authentication failed"),
            ("remote: rate limit exceeded", "rate limit exceeded"),
        ],
    )
    async def test_push_surfaces_command_failure(self, tmp_path, monkeypatch, stderr, expected):
        repo = _init_git_repo(tmp_path)

        monkeypatch.setattr(
            "api.assistant_tools.skills.git_tool.subprocess.run",
            lambda *args, **kwargs: SimpleNamespace(
                stdout="",
                stderr=stderr,
                returncode=128,
            ),
        )

        result = await TOOL_REGISTRY["git_push"].handler(repo_path=str(repo))

        assert result["returncode"] == 128
        assert "error" in result
        assert expected in result["error"].lower()
