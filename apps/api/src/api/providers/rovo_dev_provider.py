"""Rovo Dev provider — Atlassian AI coding agent (Goblin Coder).

Hybrid two-phase worker:

  Phase 1 (optional): Pull Jira/Confluence context via Atlassian MCP
                      (getTeamworkGraphContext) when ATLASSIAN_CLOUD_ID is set.

  Phase 2: Dispatch a GitHub Actions workflow (goblin-coder.yml) that runs
           atlassian-labs/rovo-dev-action with the enriched prompt.
           Poll for completion and return the resulting PR diff as ProviderResult.text.

Auth:
  - Atlassian MCP : Bearer base64(email:token) + Accept: application/json, text/event-stream
  - GitHub Actions: Authorization: Bearer <GITHUB_TOKEN>

Protocol notes:
  - MCP endpoint is SSE-based and session-scoped.
    Flow: initialize → Mcp-Session-Id header → call → parse SSE event data.
  - GitHub dispatch is a simple REST POST; polling uses /runs?event=repository_dispatch.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
import structlog

from .base import BaseProvider, ProviderHealth, ProviderResult

logger = structlog.get_logger(__name__)

_MCP_ENDPOINT = "https://mcp.atlassian.com/v1/mcp"
_GITHUB_API = "https://api.github.com"


# ---------------------------------------------------------------------------
# Atlassian MCP session helper
# ---------------------------------------------------------------------------


class _AtlassianMCPSession:
    """Manages a single stateful MCP session for one request."""

    def __init__(self, mcp_url: str, auth_header: str) -> None:
        self._url = mcp_url
        self._auth = auth_header
        self._session_id: Optional[str] = None

    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        h = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": self._auth,
        }
        if self._session_id:
            h["Mcp-Session-Id"] = self._session_id
        if extra:
            h.update(extra)
        return h

    @staticmethod
    def _parse_sse_data(raw: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from SSE event stream text."""
        for line in raw.splitlines():
            if line.startswith("data:"):
                payload = line[5:].strip()
                try:
                    return json.loads(payload)
                except json.JSONDecodeError:
                    pass
        return None

    async def initialize(self, client: httpx.AsyncClient) -> bool:
        body = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "goblin-coder", "version": "1.0"},
            },
        }
        resp = await client.post(self._url, json=body, headers=self._headers())
        if resp.status_code != 200:
            return False
        self._session_id = resp.headers.get("Mcp-Session-Id")

        # Send notifications/initialized (fire-and-forget, no response expected)
        notif = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
        await client.post(self._url, json=notif, headers=self._headers())
        return bool(self._session_id)

    async def call_tool(
        self,
        client: httpx.AsyncClient,
        name: str,
        arguments: Dict[str, Any],
        call_id: str = "1",
    ) -> Optional[Dict[str, Any]]:
        body = {
            "jsonrpc": "2.0",
            "id": call_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        resp = await client.post(self._url, json=body, headers=self._headers())
        resp.raise_for_status()
        data = self._parse_sse_data(resp.text) or resp.json()
        return data.get("result")


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class RovoDevProvider(BaseProvider):
    """Atlassian Rovo Dev coding agent — internal-only, not user-facing."""

    def __init__(
        self,
        provider_id: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(provider_id, config)
        cfg = config or {}
        self._email = os.getenv("ATLASSIAN_EMAIL", "").strip()
        self._atl_token = os.getenv("ATLASSIAN_API_TOKEN", "").strip()
        self._cloud_id = os.getenv("ATLASSIAN_CLOUD_ID", "").strip()
        self._mcp_url = (
            os.getenv("ROVO_DEV_ENDPOINT", "").strip() or str(cfg.get("endpoint", _MCP_ENDPOINT))
        ).rstrip("/")

        self._gh_token = os.getenv("GITHUB_TOKEN", "").strip()
        self._gh_owner = os.getenv("GITHUB_REPO_OWNER", "").strip()
        self._gh_repo = os.getenv("GITHUB_REPO_NAME", "").strip()

        raw_timeout = cfg.get("default_timeout_ms", 180_000)
        self._timeout_s = int(raw_timeout) / 1000

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------

    def _atlassian_bearer(self) -> str:
        encoded = base64.b64encode(f"{self._email}:{self._atl_token}".encode()).decode()
        return f"Bearer {encoded}"

    def _github_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._gh_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    # ------------------------------------------------------------------
    # Phase 1: Atlassian context enrichment (best-effort)
    # ------------------------------------------------------------------

    async def _gather_atlassian_context(self, prompt: str, client: httpx.AsyncClient) -> str:
        """Pull Teamwork Graph context if a Jira issue key is mentioned."""
        if not (self._email and self._atl_token and self._cloud_id):
            return ""

        issue_key = _extract_jira_key(prompt)
        if not issue_key:
            return ""

        try:
            session = _AtlassianMCPSession(self._mcp_url, self._atlassian_bearer())
            ok = await session.initialize(client)
            if not ok:
                return ""

            result = await session.call_tool(
                client,
                name="getTeamworkGraphContext",
                arguments={
                    "cloudId": self._cloud_id,
                    "objectType": "JiraWorkItem",
                    "objectIdentifier": issue_key,
                    "detailLevel": "summary",
                },
            )
            if result:
                return f"\n\n[Jira context for {issue_key}]\n{json.dumps(result, indent=2)}"
        except Exception as exc:
            logger.debug("rovo_dev_context_skipped", reason=str(exc))
        return ""

    # ------------------------------------------------------------------
    # Phase 2: GitHub Actions dispatch + poll
    # ------------------------------------------------------------------

    async def _dispatch_github_action(
        self,
        prompt: str,
        task_id: str,
        client: httpx.AsyncClient,
    ) -> Optional[str]:
        """Trigger goblin-coder workflow and return the diff from the PR."""
        if not (self._gh_token and self._gh_owner and self._gh_repo):
            return None

        dispatch_url = f"{_GITHUB_API}/repos/{self._gh_owner}/{self._gh_repo}/dispatches"
        body = {
            "event_type": "goblin-coder",
            "client_payload": {"prompt": prompt, "task_id": task_id},
        }
        resp = await client.post(dispatch_url, json=body, headers=self._github_headers())
        if resp.status_code not in (204, 200):
            raise RuntimeError(f"GitHub dispatch failed: HTTP {resp.status_code} {resp.text[:200]}")

        logger.info("rovo_dev_action_dispatched", task_id=task_id)

        # Poll for the workflow run to complete (max ~3 min)
        run_id = await self._wait_for_run(task_id, client)
        if run_id is None:
            raise RuntimeError("Timed out waiting for goblin-coder workflow run to start")

        diff = await self._fetch_run_diff(run_id, client)
        return diff

    async def _wait_for_run(
        self,
        task_id: str,
        client: httpx.AsyncClient,
        max_wait_s: float = 180.0,
        poll_interval_s: float = 6.0,
    ) -> Optional[int]:
        """Poll until the workflow run dispatched for task_id appears and completes."""
        runs_url = f"{_GITHUB_API}/repos/{self._gh_owner}/{self._gh_repo}/actions/workflows/goblin-coder.yml/runs"
        deadline = time.monotonic() + max_wait_s
        # Give Actions a few seconds to register the run
        await asyncio.sleep(6)

        while time.monotonic() < deadline:
            resp = await client.get(
                runs_url,
                params={"event": "repository_dispatch", "per_page": 5},
                headers=self._github_headers(),
            )
            resp.raise_for_status()
            runs = resp.json().get("workflow_runs", [])

            for run in runs:
                # Match by task_id injected into the payload
                if task_id in json.dumps(run):
                    status = run.get("status")
                    conclusion = run.get("conclusion")
                    run_id = run["id"]
                    if status == "completed":
                        if conclusion != "success":
                            raise RuntimeError(
                                f"Rovo Dev workflow run {run_id} ended with conclusion={conclusion}"
                            )
                        return run_id
                    # Still running — break inner loop and wait
                    break
            else:
                # No matching run yet — check most recent run by dispatch time
                if runs:
                    latest = runs[0]
                    if latest.get("status") == "completed":
                        if latest.get("conclusion") == "success":
                            return latest["id"]

            await asyncio.sleep(poll_interval_s)

        return None

    async def _fetch_run_diff(self, run_id: int, client: httpx.AsyncClient) -> str:
        """Find the PR created by the workflow run and fetch its diff."""
        # Look for PRs created around the time of the run
        prs_url = f"{_GITHUB_API}/repos/{self._gh_owner}/{self._gh_repo}/pulls"
        resp = await client.get(
            prs_url,
            params={"state": "open", "sort": "created", "direction": "desc", "per_page": 5},
            headers=self._github_headers(),
        )
        resp.raise_for_status()
        prs = resp.json()
        if not prs:
            return f"[Rovo Dev run {run_id} completed — no PR created]"

        # Fetch the diff of the most recent PR
        pr_number = prs[0]["number"]
        diff_resp = await client.get(
            f"{_GITHUB_API}/repos/{self._gh_owner}/{self._gh_repo}/pulls/{pr_number}",
            headers={**self._github_headers(), "Accept": "application/vnd.github.diff"},
        )
        diff_resp.raise_for_status()
        return diff_resp.text or f"[PR #{pr_number} — empty diff]"

    # ------------------------------------------------------------------
    # BaseProvider interface
    # ------------------------------------------------------------------

    def _extract_prompt(
        self,
        messages: Optional[List[Dict[str, str]]],
        kwargs: Dict[str, Any],
    ) -> str:
        normalized = self.normalize_messages(messages, **kwargs)
        for msg in reversed(normalized):
            content = str(msg.get("content", "")).strip()
            if content:
                return content
        return str(kwargs.get("prompt", "")).strip()

    async def invoke(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None,
        *,
        stream: bool = False,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        prompt: str = "",
        **kwargs: Any,
    ) -> ProviderResult:
        missing = []
        if not self._gh_token:
            missing.append("GITHUB_TOKEN")
        if not self._gh_owner:
            missing.append("GITHUB_REPO_OWNER")
        if not self._gh_repo:
            missing.append("GITHUB_REPO_NAME")
        if missing:
            return ProviderResult(
                ok=False,
                provider=self.provider_id,
                model="rovo_dev",
                error=f"Missing env vars: {', '.join(missing)}",
            )

        task_id = str(kwargs.get("task_id") or uuid.uuid4())
        base_prompt = self._extract_prompt(messages, {"prompt": prompt, **kwargs})
        if not base_prompt:
            return ProviderResult(
                ok=False,
                provider=self.provider_id,
                model="rovo_dev",
                error="Empty prompt — nothing to send to Rovo Dev",
            )

        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                # Phase 1: enrich with Atlassian context (best-effort, never blocks)
                context_blob = await self._gather_atlassian_context(base_prompt, client)
                enriched_prompt = base_prompt + context_blob

                # Phase 2: dispatch to GitHub Actions → Rovo Dev
                diff = await self._dispatch_github_action(enriched_prompt, task_id, client)

            latency = (time.perf_counter() - t0) * 1000
            if diff is None:
                raise RuntimeError("GitHub Actions dispatch unavailable")

            self.record_success()
            logger.info(
                "rovo_dev_invoke_ok",
                task_id=task_id,
                latency_ms=round(latency),
                diff_chars=len(diff),
                context_enriched=bool(context_blob),
            )
            return ProviderResult(
                ok=True,
                text=diff,
                raw={"task_id": task_id, "context_enriched": bool(context_blob)},
                provider=self.provider_id,
                model="rovo_dev",
                usage={},
                cost_usd=0.0,
                latency_ms=latency,
            )
        except Exception as exc:
            error = str(exc)
            self.record_failure(error)
            logger.warning("rovo_dev_invoke_failed", task_id=task_id, error=error)
            return ProviderResult(
                ok=False, provider=self.provider_id, model="rovo_dev", error=error
            )

    async def stream(  # type: ignore[override]
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        prompt: str = "",
        **kwargs: Any,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        result = await self.invoke(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            prompt=prompt,
            **kwargs,
        )
        if result.ok and result.text:
            yield {"text": result.text, "done": True}
        else:
            raise RuntimeError(result.error or "RovoDevProvider: empty response")

    async def health_check(self) -> ProviderHealth:
        missing = []
        if not (self._email and self._atl_token):
            missing.append("Atlassian credentials")
        if not self._gh_token:
            missing.append("GITHUB_TOKEN")
        if missing:
            return ProviderHealth(
                self.provider_id,
                False,
                error=f"Not configured: {', '.join(missing)}",
            )

        # Probe: MCP initialize (confirms Atlassian auth)
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                body = {
                    "jsonrpc": "2.0",
                    "id": 0,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "goblin-health", "version": "1.0"},
                    },
                }
                resp = await client.post(
                    self._mcp_url,
                    json=body,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json, text/event-stream",
                        "Authorization": self._atlassian_bearer(),
                    },
                )
            latency = (time.perf_counter() - t0) * 1000
            healthy = resp.status_code == 200
            return ProviderHealth(
                self.provider_id,
                healthy,
                latency_ms=latency,
                error=None if healthy else f"MCP HTTP {resp.status_code}",
            )
        except Exception as exc:
            latency = (time.perf_counter() - t0) * 1000
            return ProviderHealth(self.provider_id, False, latency_ms=latency, error=str(exc))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_jira_key(text: str) -> Optional[str]:
    """Return the first Jira issue key found in text (e.g. PROJ-123)."""
    match = re.search(r"\b([A-Z][A-Z0-9]{1,9}-\d+)\b", text)
    return match.group(1) if match else None
