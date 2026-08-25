"""Tests for the github_tool skill."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from api.assistant_tools import github_tool  # noqa: F401 - triggers registration
from api.assistant_tools.registry import TOOL_REGISTRY
from api.assistant_tools.skills.github_tool_pkg import client, handlers


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | list, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self):
        return self._payload


class _FakeAsyncClient:
    def __init__(
        self,
        *,
        get_response: _FakeResponse | None = None,
        post_response: _FakeResponse | None = None,
        **_kwargs,
    ):
        self._get_response = get_response
        self._post_response = post_response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, path, params=None):
        del path, params
        return self._get_response

    async def post(self, path, json=None):
        del path, json
        return self._post_response


class TestGitHubToolRegistration:
    EXPECTED = {
        "github_get_repo",
        "github_list_repos",
        "github_list_issues",
        "github_get_issue",
        "github_create_issue",
        "github_add_comment",
        "github_list_prs",
        "github_get_pr",
        "github_create_pr",
        "github_get_file",
        "github_search_code",
    }

    def test_github_tools_registered(self):
        assert self.EXPECTED.issubset(TOOL_REGISTRY.keys())

    def test_github_tools_have_github_category(self):
        for name in self.EXPECTED:
            assert TOOL_REGISTRY[name].category == "github"


class TestGitHubClient:
    def test_headers_include_token(self, monkeypatch):
        # client.headers() checks GH_TOKEN before GITHUB_TOKEN (see
        # _TOKEN_ENV_VARS in client.py) — a real GH_TOKEN in the host
        # environment (e.g. from `gh auth login`) would otherwise leak
        # into this test and take precedence over the mock below.
        monkeypatch.delenv("GH_TOKEN", raising=False)
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")

        headers = client.headers()

        assert headers["Authorization"] == "Bearer ghp_test"
        assert headers["Accept"] == "application/vnd.github+json"

    def test_repo_scope_is_enforced_for_repo_paths(self, monkeypatch):
        monkeypatch.setenv("AGENT_GITHUB_ALLOWED_REPOSITORY", "acme/goblin-assistant")

        with pytest.raises(ValueError, match="scoped to acme/goblin-assistant"):
            client.require_repo_scope("acme", "other-repo")

    @pytest.mark.asyncio
    async def test_repo_scoped_search_code_adds_repo_qualifier(self, monkeypatch):
        monkeypatch.setenv("AGENT_GITHUB_ALLOWED_REPOSITORY", "acme/goblin-assistant")
        response = _FakeResponse(200, {"total_count": 0, "items": []})
        seen = {}

        class _CaptureClient(_FakeAsyncClient):
            async def get(self, path, params=None):
                seen["params"] = params
                return await super().get(path, params)

        monkeypatch.setattr(
            client.httpx,
            "AsyncClient",
            lambda *args, **kwargs: _CaptureClient(get_response=response),
        )

        await handlers.handle_github_search_code("auth middleware")

        assert seen["params"]["q"].startswith("repo:acme/goblin-assistant ")

    @pytest.mark.asyncio
    async def test_get_success_returns_json(self, monkeypatch):
        monkeypatch.delenv("AGENT_GITHUB_ALLOWED_REPOSITORY", raising=False)
        monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
        response = _FakeResponse(200, {"full_name": "octo/repo"})
        monkeypatch.setattr(
            client.httpx,
            "AsyncClient",
            lambda *args, **kwargs: _FakeAsyncClient(get_response=response),
        )

        result = await client.get("/repos/octo/repo")

        assert result == {"full_name": "octo/repo"}

    @pytest.mark.asyncio
    async def test_get_rate_limit_error_returns_status(self, monkeypatch):
        response = _FakeResponse(429, {"message": "rate limit exceeded"}, text="Too Many Requests")
        monkeypatch.setattr(
            client.httpx,
            "AsyncClient",
            lambda *args, **kwargs: _FakeAsyncClient(get_response=response),
        )

        result = await client.get("/search/code", {"q": "goblin"})

        assert result == {"error": "rate limit exceeded", "status": 429}

    @pytest.mark.asyncio
    async def test_post_auth_failure_returns_status(self, monkeypatch):
        monkeypatch.delenv("AGENT_GITHUB_ALLOWED_REPOSITORY", raising=False)
        monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
        response = _FakeResponse(401, {"message": "Bad credentials"}, text="Unauthorized")
        monkeypatch.setattr(
            client.httpx,
            "AsyncClient",
            lambda *args, **kwargs: _FakeAsyncClient(post_response=response),
        )

        result = await client.post("/repos/octo/repo/issues", {"title": "Issue"})

        assert result == {"error": "Bad credentials", "status": 401}


class TestGitHubHandlers:
    @pytest.mark.asyncio
    async def test_get_repo_normalizes_success_payload(self, monkeypatch):
        monkeypatch.setattr(
            handlers,
            "get",
            AsyncMock(
                return_value={
                    "full_name": "octo/repo",
                    "description": "Repo desc",
                    "html_url": "https://github.com/octo/repo",
                    "stargazers_count": 42,
                    "forks_count": 7,
                    "open_issues_count": 3,
                    "default_branch": "main",
                    "language": "Python",
                    "private": False,
                    "topics": ["ai", "tools"],
                }
            ),
        )

        result = await handlers.handle_github_get_repo("octo", "repo")

        assert result["full_name"] == "octo/repo"
        assert result["stars"] == 42
        assert result["default_branch"] == "main"
        assert result["topics"] == ["ai", "tools"]

    @pytest.mark.asyncio
    async def test_get_repo_missing_propagates_404(self, monkeypatch):
        monkeypatch.setattr(
            handlers,
            "get",
            AsyncMock(return_value={"error": "Not Found", "status": 404}),
        )

        result = await handlers.handle_github_get_repo("octo", "missing")

        assert result == {"error": "Not Found", "status": 404}

    @pytest.mark.asyncio
    async def test_create_issue_auth_failure_propagates(self, monkeypatch):
        monkeypatch.setattr(
            handlers,
            "post",
            AsyncMock(return_value={"error": "Bad credentials", "status": 401}),
        )

        result = await handlers.handle_github_create_issue("octo", "repo", "Title")

        assert result == {"error": "Bad credentials", "status": 401}

    @pytest.mark.asyncio
    async def test_list_repos_rate_limit_propagates(self, monkeypatch):
        monkeypatch.setattr(
            handlers,
            "get",
            AsyncMock(return_value={"error": "rate limit exceeded", "status": 429}),
        )

        result = await handlers.handle_github_list_repos("octo", limit=5)

        assert result == {"error": "rate limit exceeded", "status": 429}
