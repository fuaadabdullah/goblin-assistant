"""Tests for RovoDevProvider — the Atlassian/GitHub Actions coding agent.

The provider is a two-phase worker: it optionally enriches the prompt with
Jira context over Atlassian's SSE-based MCP endpoint, then dispatches a
GitHub Actions workflow and polls it for the resulting PR diff. Both phases
are pure HTTP, so everything here drives fake clients rather than the network.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.providers.rovo_dev_provider import (
    RovoDevProvider,
    _AtlassianMCPSession,
    _extract_jira_key,
)

_GH_ENV = {
    "GH_TOKEN": "ghp_test",
    "GITHUB_REPO_OWNER": "acme",
    "GITHUB_REPO_NAME": "widgets",
}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Start every test from an unconfigured provider environment.

    The provider reads its credentials at construction time, and several of
    these names (GITHUB_TOKEN in particular) are set by the CI runner itself,
    which would otherwise decide whether a test sees a configured provider.
    """
    for name in (
        "ATLASSIAN_EMAIL",
        "ATLASSIAN_API_TOKEN",
        "ATLASSIAN_CLOUD_ID",
        "ROVO_DEV_ENDPOINT",
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "AGENT_GITHUB_TOKEN",
        "GITHUB_REPO_OWNER",
        "GITHUB_REPO_NAME",
    ):
        monkeypatch.delenv(name, raising=False)


def _provider(**config: Any) -> RovoDevProvider:
    return RovoDevProvider("rovo_dev", config or None)


class _FakeResponse:
    def __init__(
        self,
        status_code: int = 200,
        payload: Any = None,
        text: str = "",
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.headers = headers or {}

    def json(self) -> Any:
        if self._payload is None:
            raise ValueError("no json payload")
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


# ---------------------------------------------------------------------------
# _extract_jira_key
# ---------------------------------------------------------------------------


class TestExtractJiraKey:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("Fix PROJ-123 please", "PROJ-123"),
            ("GOB-7 and GOB-8 both", "GOB-7"),
            ("no key here", None),
            ("lowercase proj-123", None),
            ("", None),
        ],
    )
    def test_extracts_first_key(self, text, expected):
        assert _extract_jira_key(text) == expected

    def test_ignores_keys_without_a_number(self):
        assert _extract_jira_key("PROJECT-") is None


# ---------------------------------------------------------------------------
# _AtlassianMCPSession
# ---------------------------------------------------------------------------


class TestAtlassianMCPSession:
    def test_headers_omit_session_id_before_initialize(self):
        session = _AtlassianMCPSession("https://mcp.example", "Bearer abc")

        headers = session._headers()

        assert headers["Authorization"] == "Bearer abc"
        assert headers["Accept"] == "application/json, text/event-stream"
        assert "Mcp-Session-Id" not in headers

    def test_headers_include_session_id_and_extras(self):
        session = _AtlassianMCPSession("https://mcp.example", "Bearer abc")
        session._session_id = "sess-1"

        headers = session._headers({"X-Trace": "t-1"})

        assert headers["Mcp-Session-Id"] == "sess-1"
        assert headers["X-Trace"] == "t-1"

    def test_parse_sse_data_reads_the_data_line(self):
        raw = 'event: message\ndata: {"result": {"ok": true}}\n\n'

        assert _AtlassianMCPSession._parse_sse_data(raw) == {"result": {"ok": True}}

    def test_parse_sse_data_skips_unparsable_lines(self):
        raw = 'data: not-json\ndata: {"v": 1}\n'

        assert _AtlassianMCPSession._parse_sse_data(raw) == {"v": 1}

    def test_parse_sse_data_returns_none_without_a_data_line(self):
        assert _AtlassianMCPSession._parse_sse_data("event: ping\n") is None

    @pytest.mark.asyncio
    async def test_initialize_captures_session_id(self):
        session = _AtlassianMCPSession("https://mcp.example", "Bearer abc")
        client = MagicMock()
        client.post = AsyncMock(
            return_value=_FakeResponse(200, headers={"Mcp-Session-Id": "sess-9"})
        )

        assert await session.initialize(client) is True
        assert session._session_id == "sess-9"
        # initialize + the fire-and-forget notifications/initialized
        assert client.post.await_count == 2

    @pytest.mark.asyncio
    async def test_initialize_returns_false_on_http_error(self):
        session = _AtlassianMCPSession("https://mcp.example", "Bearer abc")
        client = MagicMock()
        client.post = AsyncMock(return_value=_FakeResponse(500))

        assert await session.initialize(client) is False
        assert client.post.await_count == 1

    @pytest.mark.asyncio
    async def test_initialize_returns_false_when_no_session_id_returned(self):
        session = _AtlassianMCPSession("https://mcp.example", "Bearer abc")
        client = MagicMock()
        client.post = AsyncMock(return_value=_FakeResponse(200, headers={}))

        assert await session.initialize(client) is False

    @pytest.mark.asyncio
    async def test_call_tool_prefers_sse_payload(self):
        session = _AtlassianMCPSession("https://mcp.example", "Bearer abc")
        client = MagicMock()
        client.post = AsyncMock(
            return_value=_FakeResponse(
                200,
                payload={"result": "from-json"},
                text='data: {"result": "from-sse"}\n',
            )
        )

        result = await session.call_tool(client, "aTool", {"k": "v"})

        assert result == "from-sse"

    @pytest.mark.asyncio
    async def test_call_tool_falls_back_to_json_body(self):
        session = _AtlassianMCPSession("https://mcp.example", "Bearer abc")
        client = MagicMock()
        client.post = AsyncMock(
            return_value=_FakeResponse(200, payload={"result": "from-json"}, text="")
        )

        assert await session.call_tool(client, "aTool", {}) == "from-json"


# ---------------------------------------------------------------------------
# Construction / auth helpers
# ---------------------------------------------------------------------------


class TestProviderConfiguration:
    def test_reads_github_token_in_priority_order(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "second")
        monkeypatch.setenv("AGENT_GITHUB_TOKEN", "third")

        assert _provider()._gh_token == "second"

        monkeypatch.setenv("GH_TOKEN", "first")
        assert _provider()._gh_token == "first"

    def test_endpoint_env_overrides_config(self, monkeypatch):
        monkeypatch.setenv("ROVO_DEV_ENDPOINT", "https://env.example/mcp/")

        assert _provider(endpoint="https://config.example")._mcp_url == "https://env.example/mcp"

    def test_falls_back_to_config_endpoint_then_default(self):
        assert _provider(endpoint="https://config.example/")._mcp_url == "https://config.example"
        assert _provider()._mcp_url == "https://mcp.atlassian.com/v1/mcp"

    def test_timeout_is_converted_from_milliseconds(self):
        assert _provider(default_timeout_ms=45_000)._timeout_s == 45.0

    def test_atlassian_bearer_is_base64_basic_credentials(self, monkeypatch):
        monkeypatch.setenv("ATLASSIAN_EMAIL", "dev@example.com")
        monkeypatch.setenv("ATLASSIAN_API_TOKEN", "tok")
        import base64

        expected = base64.b64encode(b"dev@example.com:tok").decode()

        assert _provider()._atlassian_bearer() == f"Bearer {expected}"

    def test_github_headers_pin_the_api_version(self, monkeypatch):
        monkeypatch.setenv("GH_TOKEN", "ghp_x")

        headers = _provider()._github_headers()

        assert headers["Authorization"] == "Bearer ghp_x"
        assert headers["Accept"] == "application/vnd.github+json"
        assert headers["X-GitHub-Api-Version"] == "2022-11-28"


# ---------------------------------------------------------------------------
# _extract_prompt
# ---------------------------------------------------------------------------


class TestExtractPrompt:
    def test_takes_the_last_non_empty_message(self):
        provider = _provider()

        prompt = provider._extract_prompt(
            [
                {"role": "user", "content": "first"},
                {"role": "assistant", "content": "second"},
            ],
            {},
        )

        assert prompt == "second"

    def test_skips_blank_trailing_messages(self):
        provider = _provider()

        prompt = provider._extract_prompt(
            [{"role": "user", "content": "real"}, {"role": "user", "content": "   "}],
            {},
        )

        assert prompt == "real"

    def test_falls_back_to_prompt_kwarg(self):
        provider = _provider()

        assert provider._extract_prompt(None, {"prompt": "from-kwarg"}) == "from-kwarg"


# ---------------------------------------------------------------------------
# Atlassian context enrichment
# ---------------------------------------------------------------------------


class TestGatherAtlassianContext:
    @pytest.mark.asyncio
    async def test_returns_empty_without_credentials(self):
        provider = _provider()

        assert await provider._gather_atlassian_context("PROJ-1", MagicMock()) == ""

    @pytest.mark.asyncio
    async def test_returns_empty_when_prompt_has_no_issue_key(self, monkeypatch):
        monkeypatch.setenv("ATLASSIAN_EMAIL", "dev@example.com")
        monkeypatch.setenv("ATLASSIAN_API_TOKEN", "tok")
        monkeypatch.setenv("ATLASSIAN_CLOUD_ID", "cloud-1")

        assert await _provider()._gather_atlassian_context("no key", MagicMock()) == ""

    @pytest.mark.asyncio
    async def test_includes_the_tool_result_for_a_referenced_issue(self, monkeypatch):
        monkeypatch.setenv("ATLASSIAN_EMAIL", "dev@example.com")
        monkeypatch.setenv("ATLASSIAN_API_TOKEN", "tok")
        monkeypatch.setenv("ATLASSIAN_CLOUD_ID", "cloud-1")
        provider = _provider()

        with (
            patch.object(_AtlassianMCPSession, "initialize", AsyncMock(return_value=True)),
            patch.object(
                _AtlassianMCPSession,
                "call_tool",
                AsyncMock(return_value={"summary": "Fix the thing"}),
            ) as call_tool,
        ):
            blob = await provider._gather_atlassian_context("Handle PROJ-42", MagicMock())

        assert "[Jira context for PROJ-42]" in blob
        assert "Fix the thing" in blob
        assert call_tool.await_args.kwargs["arguments"]["objectIdentifier"] == "PROJ-42"

    @pytest.mark.asyncio
    async def test_returns_empty_when_the_session_cannot_initialize(self, monkeypatch):
        monkeypatch.setenv("ATLASSIAN_EMAIL", "dev@example.com")
        monkeypatch.setenv("ATLASSIAN_API_TOKEN", "tok")
        monkeypatch.setenv("ATLASSIAN_CLOUD_ID", "cloud-1")

        with patch.object(_AtlassianMCPSession, "initialize", AsyncMock(return_value=False)):
            blob = await _provider()._gather_atlassian_context("PROJ-42", MagicMock())

        assert blob == ""

    @pytest.mark.asyncio
    async def test_swallows_mcp_errors(self, monkeypatch):
        # Enrichment is best-effort and must never fail the actual request.
        monkeypatch.setenv("ATLASSIAN_EMAIL", "dev@example.com")
        monkeypatch.setenv("ATLASSIAN_API_TOKEN", "tok")
        monkeypatch.setenv("ATLASSIAN_CLOUD_ID", "cloud-1")

        with patch.object(
            _AtlassianMCPSession, "initialize", AsyncMock(side_effect=RuntimeError("boom"))
        ):
            blob = await _provider()._gather_atlassian_context("PROJ-42", MagicMock())

        assert blob == ""


# ---------------------------------------------------------------------------
# GitHub dispatch / polling
# ---------------------------------------------------------------------------


class TestDispatchGithubAction:
    @pytest.mark.asyncio
    async def test_returns_none_when_github_is_unconfigured(self):
        assert await _provider()._dispatch_github_action("p", "t", MagicMock()) is None

    @pytest.mark.asyncio
    async def test_raises_when_dispatch_is_rejected(self, monkeypatch):
        for key, value in _GH_ENV.items():
            monkeypatch.setenv(key, value)
        client = MagicMock()
        client.post = AsyncMock(return_value=_FakeResponse(422, text="bad payload"))

        with pytest.raises(RuntimeError, match="GitHub dispatch failed: HTTP 422"):
            await _provider()._dispatch_github_action("p", "task-1", client)

    @pytest.mark.asyncio
    async def test_raises_when_the_run_never_appears(self, monkeypatch):
        for key, value in _GH_ENV.items():
            monkeypatch.setenv(key, value)
        client = MagicMock()
        client.post = AsyncMock(return_value=_FakeResponse(204))
        provider = _provider()

        with patch.object(provider, "_wait_for_run", AsyncMock(return_value=None)):
            with pytest.raises(RuntimeError, match="Timed out waiting"):
                await provider._dispatch_github_action("p", "task-1", client)

    @pytest.mark.asyncio
    async def test_returns_the_run_diff_on_success(self, monkeypatch):
        for key, value in _GH_ENV.items():
            monkeypatch.setenv(key, value)
        client = MagicMock()
        client.post = AsyncMock(return_value=_FakeResponse(204))
        provider = _provider()

        with (
            patch.object(provider, "_wait_for_run", AsyncMock(return_value=99)),
            patch.object(provider, "_fetch_run_diff", AsyncMock(return_value="--- diff ---")),
        ):
            diff = await provider._dispatch_github_action("p", "task-1", client)

        assert diff == "--- diff ---"


class TestWaitForRun:
    @pytest.mark.asyncio
    async def test_returns_run_id_when_matching_run_succeeded(self, monkeypatch):
        for key, value in _GH_ENV.items():
            monkeypatch.setenv(key, value)
        run = {"id": 7, "status": "completed", "conclusion": "success", "name": "task-1"}
        client = MagicMock()
        client.get = AsyncMock(return_value=_FakeResponse(200, payload={"workflow_runs": [run]}))

        with patch("api.providers.rovo_dev_provider.asyncio.sleep", AsyncMock()):
            assert await _provider()._wait_for_run("task-1", client) == 7

    @pytest.mark.asyncio
    async def test_raises_when_matching_run_failed(self, monkeypatch):
        for key, value in _GH_ENV.items():
            monkeypatch.setenv(key, value)
        run = {"id": 8, "status": "completed", "conclusion": "failure", "name": "task-1"}
        client = MagicMock()
        client.get = AsyncMock(return_value=_FakeResponse(200, payload={"workflow_runs": [run]}))

        with patch("api.providers.rovo_dev_provider.asyncio.sleep", AsyncMock()):
            with pytest.raises(RuntimeError, match="conclusion=failure"):
                await _provider()._wait_for_run("task-1", client)

    @pytest.mark.asyncio
    async def test_accepts_latest_successful_run_when_task_id_is_absent(self, monkeypatch):
        for key, value in _GH_ENV.items():
            monkeypatch.setenv(key, value)
        run = {"id": 11, "status": "completed", "conclusion": "success", "name": "other"}
        client = MagicMock()
        client.get = AsyncMock(return_value=_FakeResponse(200, payload={"workflow_runs": [run]}))

        with patch("api.providers.rovo_dev_provider.asyncio.sleep", AsyncMock()):
            assert await _provider()._wait_for_run("task-1", client) == 11

    @pytest.mark.asyncio
    async def test_returns_none_once_the_deadline_passes(self, monkeypatch):
        for key, value in _GH_ENV.items():
            monkeypatch.setenv(key, value)
        client = MagicMock()
        client.get = AsyncMock(return_value=_FakeResponse(200, payload={"workflow_runs": []}))

        with patch("api.providers.rovo_dev_provider.asyncio.sleep", AsyncMock()):
            result = await _provider()._wait_for_run("task-1", client, max_wait_s=0.0)

        assert result is None


class TestFetchRunDiff:
    @pytest.mark.asyncio
    async def test_reports_when_no_pr_was_created(self, monkeypatch):
        for key, value in _GH_ENV.items():
            monkeypatch.setenv(key, value)
        client = MagicMock()
        client.get = AsyncMock(return_value=_FakeResponse(200, payload=[]))

        assert "no PR created" in await _provider()._fetch_run_diff(5, client)

    @pytest.mark.asyncio
    async def test_returns_the_diff_of_the_newest_pr(self, monkeypatch):
        for key, value in _GH_ENV.items():
            monkeypatch.setenv(key, value)
        client = MagicMock()
        client.get = AsyncMock(
            side_effect=[
                _FakeResponse(200, payload=[{"number": 42}]),
                _FakeResponse(200, text="--- a/x\n+++ b/x\n"),
            ]
        )

        diff = await _provider()._fetch_run_diff(5, client)

        assert diff == "--- a/x\n+++ b/x\n"

    @pytest.mark.asyncio
    async def test_notes_an_empty_diff(self, monkeypatch):
        for key, value in _GH_ENV.items():
            monkeypatch.setenv(key, value)
        client = MagicMock()
        client.get = AsyncMock(
            side_effect=[
                _FakeResponse(200, payload=[{"number": 42}]),
                _FakeResponse(200, text=""),
            ]
        )

        assert await _provider()._fetch_run_diff(5, client) == "[PR #42 — empty diff]"


# ---------------------------------------------------------------------------
# invoke / stream / health_check
# ---------------------------------------------------------------------------


class TestInvoke:
    @pytest.mark.asyncio
    async def test_reports_every_missing_env_var(self):
        result = await _provider().invoke(prompt="do the thing")

        assert result.ok is False
        assert "GH_TOKEN" in result.error
        assert "GITHUB_REPO_OWNER" in result.error
        assert "GITHUB_REPO_NAME" in result.error

    @pytest.mark.asyncio
    async def test_rejects_an_empty_prompt(self, monkeypatch):
        for key, value in _GH_ENV.items():
            monkeypatch.setenv(key, value)

        result = await _provider().invoke(messages=[{"role": "user", "content": "  "}])

        assert result.ok is False
        assert "Empty prompt" in result.error

    @pytest.mark.asyncio
    async def test_returns_the_diff_and_records_success(self, monkeypatch):
        for key, value in _GH_ENV.items():
            monkeypatch.setenv(key, value)
        provider = _provider()

        with (
            patch.object(provider, "_gather_atlassian_context", AsyncMock(return_value="\n[ctx]")),
            patch.object(
                provider, "_dispatch_github_action", AsyncMock(return_value="the diff")
            ) as dispatch,
            patch.object(provider, "record_success") as record_success,
        ):
            result = await provider.invoke(prompt="ship it", task_id="task-7")

        assert result.ok is True
        assert result.text == "the diff"
        assert result.raw == {"task_id": "task-7", "context_enriched": True}
        assert result.cost_usd == 0.0
        record_success.assert_called_once()
        # The enriched prompt, not the bare one, is what gets dispatched.
        assert dispatch.await_args.args[0] == "ship it\n[ctx]"

    @pytest.mark.asyncio
    async def test_dispatch_returning_none_is_an_error(self, monkeypatch):
        for key, value in _GH_ENV.items():
            monkeypatch.setenv(key, value)
        provider = _provider()

        with (
            patch.object(provider, "_gather_atlassian_context", AsyncMock(return_value="")),
            patch.object(provider, "_dispatch_github_action", AsyncMock(return_value=None)),
            patch.object(provider, "record_failure") as record_failure,
        ):
            result = await provider.invoke(prompt="ship it")

        assert result.ok is False
        assert "dispatch unavailable" in result.error
        record_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_records_failure_when_dispatch_raises(self, monkeypatch):
        for key, value in _GH_ENV.items():
            monkeypatch.setenv(key, value)
        provider = _provider()

        with (
            patch.object(provider, "_gather_atlassian_context", AsyncMock(return_value="")),
            patch.object(
                provider, "_dispatch_github_action", AsyncMock(side_effect=RuntimeError("nope"))
            ),
            patch.object(provider, "record_failure") as record_failure,
        ):
            result = await provider.invoke(prompt="ship it")

        assert result.ok is False
        assert result.error == "nope"
        record_failure.assert_called_once_with("nope")


class TestStream:
    @pytest.mark.asyncio
    async def test_yields_a_single_terminal_chunk(self, monkeypatch):
        for key, value in _GH_ENV.items():
            monkeypatch.setenv(key, value)
        provider = _provider()

        with (
            patch.object(provider, "_gather_atlassian_context", AsyncMock(return_value="")),
            patch.object(provider, "_dispatch_github_action", AsyncMock(return_value="d")),
        ):
            chunks = [chunk async for chunk in provider.stream(prompt="go")]

        assert chunks == [{"text": "d", "done": True}]

    @pytest.mark.asyncio
    async def test_raises_when_the_underlying_invoke_failed(self):
        provider = _provider()

        with pytest.raises(RuntimeError, match="Missing env vars"):
            [chunk async for chunk in provider.stream(prompt="go")]


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_unhealthy_without_credentials(self):
        health = await _provider().health_check()

        assert health.healthy is False
        assert "Atlassian credentials" in health.error
        assert "GH_TOKEN" in health.error

    @pytest.mark.asyncio
    async def test_healthy_when_mcp_initialize_succeeds(self, monkeypatch):
        monkeypatch.setenv("ATLASSIAN_EMAIL", "dev@example.com")
        monkeypatch.setenv("ATLASSIAN_API_TOKEN", "tok")
        monkeypatch.setenv("GH_TOKEN", "ghp_x")

        client = MagicMock()
        client.post = AsyncMock(return_value=_FakeResponse(200))
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=client):
            health = await _provider().health_check()

        assert health.healthy is True
        assert health.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_unhealthy_on_mcp_http_error(self, monkeypatch):
        monkeypatch.setenv("ATLASSIAN_EMAIL", "dev@example.com")
        monkeypatch.setenv("ATLASSIAN_API_TOKEN", "tok")
        monkeypatch.setenv("GH_TOKEN", "ghp_x")

        client = MagicMock()
        client.post = AsyncMock(return_value=_FakeResponse(401))
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=client):
            health = await _provider().health_check()

        assert health.healthy is False
        assert health.error == "MCP HTTP 401"

    @pytest.mark.asyncio
    async def test_unhealthy_when_the_probe_raises(self, monkeypatch):
        monkeypatch.setenv("ATLASSIAN_EMAIL", "dev@example.com")
        monkeypatch.setenv("ATLASSIAN_API_TOKEN", "tok")
        monkeypatch.setenv("GH_TOKEN", "ghp_x")

        with patch("httpx.AsyncClient", side_effect=RuntimeError("no network")):
            health = await _provider().health_check()

        assert health.healthy is False
        assert health.error == "no network"


def test_dispatch_body_carries_the_task_id(monkeypatch):
    """The polling loop matches runs by task_id, so it must be in the payload."""
    for key, value in _GH_ENV.items():
        monkeypatch.setenv(key, value)
    provider = _provider()
    captured: Dict[str, Any] = {}

    class _CapturingClient:
        async def post(self, url, json=None, headers=None):
            captured["url"] = url
            captured["json"] = json
            return _FakeResponse(204)

    async def _run():
        with (
            patch.object(provider, "_wait_for_run", AsyncMock(return_value=1)),
            patch.object(provider, "_fetch_run_diff", AsyncMock(return_value="d")),
        ):
            await provider._dispatch_github_action("prompt", "task-abc", _CapturingClient())

    import asyncio as _asyncio

    _asyncio.run(_run())

    assert captured["url"].endswith("/repos/acme/widgets/dispatches")
    assert captured["json"]["event_type"] == "goblin-coder"
    assert captured["json"]["client_payload"]["task_id"] == "task-abc"
    assert "task-abc" in json.dumps(captured["json"])
