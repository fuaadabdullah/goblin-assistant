"""
Tests for the terminal_tool skill.
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

import api.assistant_tools.skills.terminal_tool  # noqa: F401 — triggers registration
from api.assistant_tools.registry import TOOL_REGISTRY


def _mock_proc(stdout="", stderr="", returncode=0):
    m = MagicMock()
    m.stdout = stdout
    m.stderr = stderr
    m.returncode = returncode
    return m


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestTerminalToolRegistration:
    def test_run_shell_command_registered(self):
        assert "run_shell_command" in TOOL_REGISTRY

    def test_has_valid_openai_schema(self):
        schema = TOOL_REGISTRY["run_shell_command"].to_openai_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "run_shell_command"
        assert "parameters" in schema["function"]

    def test_has_terminal_category(self):
        assert TOOL_REGISTRY["run_shell_command"].category == "terminal"

    def test_has_handler(self):
        assert TOOL_REGISTRY["run_shell_command"].handler is not None


# ---------------------------------------------------------------------------
# run_shell_command
# ---------------------------------------------------------------------------


class TestRunShellCommand:
    @pytest.mark.asyncio
    async def test_empty_command_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        result = await TOOL_REGISTRY["run_shell_command"].handler(command="   ")
        assert "error" in result
        assert "empty" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_successful_command_returns_stdout(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        with patch("subprocess.run", return_value=_mock_proc(stdout="hello\n")):
            result = await TOOL_REGISTRY["run_shell_command"].handler(command="echo hello")
        assert result["exit_code"] == 0
        assert "hello" in result["stdout"]
        assert "error" not in result
        assert "elapsed_ms" in result
        assert "working_directory" in result

    @pytest.mark.asyncio
    async def test_elapsed_ms_is_non_negative_int(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        with patch("subprocess.run", return_value=_mock_proc()):
            result = await TOOL_REGISTRY["run_shell_command"].handler(command="true")
        assert isinstance(result["elapsed_ms"], int)
        assert result["elapsed_ms"] >= 0

    @pytest.mark.asyncio
    async def test_stderr_captured(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        with patch(
            "subprocess.run",
            return_value=_mock_proc(stderr="some warning", returncode=1),
        ):
            result = await TOOL_REGISTRY["run_shell_command"].handler(command="ls /nonexistent")
        assert result["stderr"] == "some warning"
        assert result["exit_code"] == 1

    @pytest.mark.asyncio
    async def test_path_traversal_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        result = await TOOL_REGISTRY["run_shell_command"].handler(
            command="ls", working_directory="../../etc"
        )
        assert "error" in result
        assert "outside" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_nonexistent_working_directory_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        result = await TOOL_REGISTRY["run_shell_command"].handler(
            command="ls", working_directory="nonexistent_subdir_xyz"
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_working_directory_in_result(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        subdir = tmp_path / "mysubdir"
        subdir.mkdir()
        with patch("subprocess.run", return_value=_mock_proc()):
            result = await TOOL_REGISTRY["run_shell_command"].handler(
                command="ls", working_directory="mysubdir"
            )
        assert "mysubdir" in result["working_directory"]

    @pytest.mark.asyncio
    async def test_command_not_found_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result = await TOOL_REGISTRY["run_shell_command"].handler(
                command="gobbledygook_command_that_does_not_exist"
            )
        assert "error" in result
        assert result["exit_code"] == -1

    @pytest.mark.asyncio
    async def test_timeout_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=[], timeout=30),
        ):
            result = await TOOL_REGISTRY["run_shell_command"].handler(command="sleep 999")
        assert "error" in result
        assert "timed out" in result["error"].lower()
        assert result["exit_code"] == -1

    @pytest.mark.asyncio
    async def test_shlex_parse_error_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        result = await TOOL_REGISTRY["run_shell_command"].handler(command="echo 'unclosed quote")
        assert "error" in result
        assert "parse" in result["error"].lower() or "quote" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_shell_false_cmd_is_list(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        captured = {}

        def capture_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return _mock_proc()

        with patch("subprocess.run", side_effect=capture_run):
            await TOOL_REGISTRY["run_shell_command"].handler(command="echo hello world")

        assert isinstance(captured["cmd"], list), "cmd must be a list (shell=False)"
        assert captured["cmd"] == ["echo", "hello", "world"]

    @pytest.mark.asyncio
    async def test_timeout_is_30s(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        captured = {}

        def capture_run(cmd, **kwargs):
            captured["timeout"] = kwargs.get("timeout")
            return _mock_proc()

        with patch("subprocess.run", side_effect=capture_run):
            await TOOL_REGISTRY["run_shell_command"].handler(command="ls")

        assert captured["timeout"] == 30
