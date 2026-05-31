"""
Tests for the sandbox_tool skill.
"""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

import api.assistant_tools.skills.sandbox_tool  # noqa: F401 — triggers registration
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


class TestSandboxToolRegistration:
    EXPECTED = {"execute_code", "run_sandbox_template"}

    def test_all_tools_registered(self):
        assert self.EXPECTED.issubset(TOOL_REGISTRY.keys())

    def test_all_tools_have_valid_openai_schema(self):
        for name in self.EXPECTED:
            schema = TOOL_REGISTRY[name].to_openai_schema()
            assert schema["type"] == "function"
            assert "name" in schema["function"]
            assert "parameters" in schema["function"]

    def test_all_tools_have_terminal_category(self):
        for name in self.EXPECTED:
            assert TOOL_REGISTRY[name].category == "terminal"

    def test_execute_code_has_handler(self):
        assert TOOL_REGISTRY["execute_code"].handler is not None

    def test_run_sandbox_template_has_handler(self):
        assert TOOL_REGISTRY["run_sandbox_template"].handler is not None


# ---------------------------------------------------------------------------
# execute_code
# ---------------------------------------------------------------------------


class TestExecuteCode:
    @pytest.mark.asyncio
    async def test_empty_code_returns_error(self):
        result = await TOOL_REGISTRY["execute_code"].handler(code="   ")
        assert "error" in result
        assert "empty" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_unsupported_language_returns_error(self):
        result = await TOOL_REGISTRY["execute_code"].handler(
            code='print(1)', language="ruby"
        )
        assert "error" in result
        assert "unsupported" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_successful_python_execution(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SANDBOX_ENABLED", "false")
        with patch("subprocess.run", return_value=_mock_proc(stdout="hello\n")):
            result = await TOOL_REGISTRY["execute_code"].handler(
                code='print("hello")', language="python"
            )
        assert result["exit_code"] == 0
        assert "hello" in result["stdout"]
        assert "error" not in result
        assert result["truncated"] is False

    @pytest.mark.asyncio
    async def test_stdout_capped_at_10kb(self, monkeypatch):
        monkeypatch.setenv("SANDBOX_ENABLED", "false")
        big_output = "x" * 20_000
        with patch("subprocess.run", return_value=_mock_proc(stdout=big_output)):
            result = await TOOL_REGISTRY["execute_code"].handler(code='print("x"*20000)')
        assert len(result["stdout"]) <= 10 * 1024
        assert result["truncated"] is True

    @pytest.mark.asyncio
    async def test_timeout_returns_error(self, monkeypatch):
        monkeypatch.setenv("SANDBOX_ENABLED", "false")
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=[], timeout=1),
        ):
            result = await TOOL_REGISTRY["execute_code"].handler(
                code="import time; time.sleep(999)", timeout=1
            )
        assert "error" in result
        assert "timed out" in result["error"].lower()
        assert result["exit_code"] == -1

    @pytest.mark.asyncio
    async def test_nonzero_exit_code_in_result(self, monkeypatch):
        monkeypatch.setenv("SANDBOX_ENABLED", "false")
        with patch(
            "subprocess.run",
            return_value=_mock_proc(stderr="NameError", returncode=1),
        ):
            result = await TOOL_REGISTRY["execute_code"].handler(
                code="undefined_var", language="python"
            )
        assert result["exit_code"] == 1
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_sandbox_enabled_uses_docker(self, monkeypatch):
        monkeypatch.setenv("SANDBOX_ENABLED", "true")
        monkeypatch.setenv("SANDBOX_IMAGE", "test-image:latest")
        captured = {}

        def capture_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return _mock_proc(stdout="ok\n")

        with patch("subprocess.run", side_effect=capture_run):
            result = await TOOL_REGISTRY["execute_code"].handler(code='print("ok")')

        cmd = captured["cmd"]
        assert "docker" in cmd[0]
        assert "--network" in cmd
        assert cmd[cmd.index("--network") + 1] == "none"
        assert "test-image:latest" in cmd
        assert "--cap-drop" in cmd
        assert cmd[cmd.index("--cap-drop") + 1] == "all"
        assert "--security-opt" in cmd
        assert "no-new-privileges" in cmd[cmd.index("--security-opt") + 1]
        assert "--user" in cmd
        assert "--tmpfs" in cmd
        assert "/tmp" in cmd[cmd.index("--tmpfs") + 1]

    @pytest.mark.asyncio
    async def test_sandbox_disabled_uses_direct_interpreter(self, monkeypatch):
        monkeypatch.setenv("SANDBOX_ENABLED", "false")
        captured = {}

        def capture_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return _mock_proc(stdout="hi\n")

        with patch("subprocess.run", side_effect=capture_run):
            await TOOL_REGISTRY["execute_code"].handler(code='print("hi")')

        assert "docker" not in captured["cmd"][0]
        assert "python" in captured["cmd"][0]

    @pytest.mark.asyncio
    async def test_timeout_clamped_to_120(self, monkeypatch):
        monkeypatch.setenv("SANDBOX_ENABLED", "false")
        captured = {}

        def capture_run(cmd, **kwargs):
            captured["kwargs"] = kwargs
            return _mock_proc()

        with patch("subprocess.run", side_effect=capture_run):
            await TOOL_REGISTRY["execute_code"].handler(
                code='pass', timeout=9999
            )

        assert captured["kwargs"]["timeout"] <= 120

    @pytest.mark.asyncio
    async def test_javascript_language_uses_node(self, monkeypatch):
        monkeypatch.setenv("SANDBOX_ENABLED", "false")
        captured = {}

        def capture_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return _mock_proc(stdout="1\n")

        with patch("subprocess.run", side_effect=capture_run):
            await TOOL_REGISTRY["execute_code"].handler(
                code="console.log(1)", language="javascript"
            )

        assert "node" in captured["cmd"][0]


# ---------------------------------------------------------------------------
# run_sandbox_template
# ---------------------------------------------------------------------------


class TestRunSandboxTemplate:
    @pytest.mark.asyncio
    async def test_unknown_template_returns_error(self):
        result = await TOOL_REGISTRY["run_sandbox_template"].handler(
            template_name="nonexistent_xyz",
            parameters="{}",
        )
        assert "error" in result
        assert "nonexistent_xyz" in result["error"]
        assert "compound_interest" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_json_parameters_returns_error(self):
        result = await TOOL_REGISTRY["run_sandbox_template"].handler(
            template_name="compound_interest",
            parameters="{not valid json}",
        )
        assert "error" in result
        assert "json" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_non_dict_json_returns_error(self):
        result = await TOOL_REGISTRY["run_sandbox_template"].handler(
            template_name="compound_interest",
            parameters="[1, 2, 3]",
        )
        assert "error" in result
        assert ("object" in result["error"].lower() or "dict" in result["error"].lower())

    @pytest.mark.asyncio
    async def test_known_template_renders_and_runs(self, monkeypatch):
        monkeypatch.setenv("SANDBOX_ENABLED", "false")
        output = json.dumps({"final_balance": 1126.83, "yearly_breakdown": []})
        with patch("subprocess.run", return_value=_mock_proc(stdout=output)):
            result = await TOOL_REGISTRY["run_sandbox_template"].handler(
                template_name="compound_interest",
                parameters=json.dumps({
                    "principal": 1000,
                    "annual_rate": 0.12,
                    "years": 1,
                    "monthly_contribution": 0,
                }),
            )
        assert result["exit_code"] == 0
        assert "error" not in result
        assert "1126" in result["stdout"]

    @pytest.mark.asyncio
    async def test_template_timeout_is_60s(self, monkeypatch):
        monkeypatch.setenv("SANDBOX_ENABLED", "false")
        captured = {}

        def capture_run(cmd, **kwargs):
            captured["timeout"] = kwargs.get("timeout")
            return _mock_proc(stdout="{}")

        with patch("subprocess.run", side_effect=capture_run):
            await TOOL_REGISTRY["run_sandbox_template"].handler(
                template_name="compound_interest",
                parameters=json.dumps({
                    "principal": 1000,
                    "annual_rate": 0.07,
                    "years": 1,
                    "monthly_contribution": 0,
                }),
            )

        assert captured["timeout"] == 60
