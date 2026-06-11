"""Tests for departments/dispatcher.py — DepartmentDispatcher chain logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.departments.dispatcher import DepartmentDispatcher
from api.departments.models import DepartmentId, DepartmentSelection

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _selection(
    department_id=DepartmentId.GENERAL,
    resolved_provider="openai",
    resolved_model="gpt-4o-mini",
    reason="test",
) -> DepartmentSelection:
    return DepartmentSelection(
        department_id=department_id,
        reason=reason,
        resolved_provider=resolved_provider,
        resolved_model=resolved_model,
    )


def _available_provider():
    p = MagicMock()
    p.is_available.return_value = True
    return p


def _unavailable_provider():
    p = MagicMock()
    p.is_available.return_value = False
    p.circuit_state = "open"
    return p


# ── _build_chain ──────────────────────────────────────────────────────────────


class TestBuildChain:
    def test_primary_provider_is_first_in_chain(self):
        dispatcher = DepartmentDispatcher()
        sel = _selection(resolved_provider="openai", resolved_model="gpt-4o-mini")
        chain = dispatcher._build_chain(sel)
        assert chain[0][0] == "openai"

    def test_fallback_providers_appended_after_primary(self):
        dispatcher = DepartmentDispatcher()
        sel = _selection(department_id=DepartmentId.CODING, resolved_provider="anthropic")
        chain = dispatcher._build_chain(sel)
        provider_ids = [p for p, _ in chain]
        assert "anthropic" in provider_ids
        assert len(chain) > 1  # must have fallbacks from policy

    def test_no_duplicates_in_chain(self):
        dispatcher = DepartmentDispatcher()
        sel = _selection(department_id=DepartmentId.GENERAL, resolved_provider="openai")
        chain = dispatcher._build_chain(sel)
        keys = [f"{p}:{m}" for p, m in chain]
        assert len(keys) == len(set(keys))

    def test_empty_resolved_provider_uses_policy_chain(self):
        dispatcher = DepartmentDispatcher()
        sel = _selection(resolved_provider="", resolved_model="")
        chain = dispatcher._build_chain(sel)
        # Should contain fallback providers from GENERAL policy
        assert len(chain) > 0


# ── _reorder_chain_by_bandit ──────────────────────────────────────────────────


class TestReorderChainByBandit:
    def test_single_item_unchanged(self):
        dispatcher = DepartmentDispatcher()
        chain = [("openai", "gpt-4o")]
        result = dispatcher._reorder_chain_by_bandit(chain, "chat")
        assert result == chain

    def test_empty_chain_unchanged(self):
        dispatcher = DepartmentDispatcher()
        result = dispatcher._reorder_chain_by_bandit([], "chat")
        assert result == []

    def test_falls_back_gracefully_on_import_error(self):
        dispatcher = DepartmentDispatcher()
        chain = [("openai", "gpt-4o"), ("anthropic", "claude")]
        with patch.dict("sys.modules", {"api.routing.ml_router": None}):
            result = dispatcher._reorder_chain_by_bandit(chain, "chat")
        assert set(p for p, _ in result) == {"openai", "anthropic"}

    def test_preserves_all_providers(self):
        dispatcher = DepartmentDispatcher()
        chain = [("openai", "gpt-4o"), ("anthropic", "claude"), ("gemini", "flash")]
        with patch.dict(
            "sys.modules",
            {
                "api.routing.ml_router": MagicMock(
                    bandit_cache=MagicMock(
                        get=lambda _t, _p: MagicMock(observation_count=0, alpha=1.0, beta=1.0)
                    ),
                    _MIN_OBSERVATIONS=5,
                )
            },
        ):
            result = dispatcher._reorder_chain_by_bandit(chain, "chat")
        assert {p for p, _ in result} == {"openai", "anthropic", "gemini"}


# ── dispatch (happy path) ─────────────────────────────────────────────────────


class TestDispatchHappyPath:
    @pytest.mark.asyncio
    async def test_successful_dispatch_returns_ok_dict(self):
        dispatcher = DepartmentDispatcher()
        sel = _selection()
        fake_result = {"ok": True, "text": "hello world", "provider": "openai"}

        with patch("api.departments.dispatcher._provider_dispatcher") as mock_pd:
            mock_pd.get_provider.return_value = _available_provider()
            mock_pd.invoke = AsyncMock(return_value=fake_result)

            result = await dispatcher.dispatch(sel, {"messages": []})

        assert result["ok"] is True
        assert result["text"] == "hello world"

    @pytest.mark.asyncio
    async def test_result_annotated_with_department(self):
        dispatcher = DepartmentDispatcher()
        sel = _selection(department_id=DepartmentId.CODING)

        with patch("api.departments.dispatcher._provider_dispatcher") as mock_pd:
            mock_pd.get_provider.return_value = _available_provider()
            mock_pd.invoke = AsyncMock(return_value={"ok": True, "text": "code here"})

            result = await dispatcher.dispatch(sel, {})

        assert result["_department"] == "coding"
        assert result["_department_reason"] == "test"

    @pytest.mark.asyncio
    async def test_model_injected_into_payload(self):
        dispatcher = DepartmentDispatcher()
        sel = _selection(resolved_model="gpt-4o-mini")
        captured = {}

        async def capture_invoke(pid, model, payload, **kwargs):
            captured["model"] = model
            return {"ok": True}

        with patch("api.departments.dispatcher._provider_dispatcher") as mock_pd:
            mock_pd.get_provider.return_value = _available_provider()
            mock_pd.invoke.side_effect = capture_invoke

            await dispatcher.dispatch(sel, {})

        assert captured["model"] == "gpt-4o-mini"


# ── dispatch (failure paths) ──────────────────────────────────────────────────


class TestDispatchFailure:
    @pytest.mark.asyncio
    async def test_unavailable_provider_skipped(self):
        dispatcher = DepartmentDispatcher()
        sel = _selection(department_id=DepartmentId.GENERAL, resolved_provider="openai")
        called_with = []

        async def invoke(pid, model, payload, **kwargs):
            called_with.append(pid)
            return {"ok": True}

        with patch("api.departments.dispatcher._provider_dispatcher") as mock_pd:

            def get_provider(pid):
                if pid == "openai":
                    return _unavailable_provider()
                return _available_provider()

            mock_pd.get_provider.side_effect = get_provider
            mock_pd.invoke.side_effect = invoke

            await dispatcher.dispatch(sel, {})

        assert "openai" not in called_with

    @pytest.mark.asyncio
    async def test_provider_returns_ok_false_tries_next(self):
        dispatcher = DepartmentDispatcher()
        sel = _selection(department_id=DepartmentId.GENERAL, resolved_provider="openai")
        calls = []

        async def invoke(pid, model, payload, **kwargs):
            calls.append(pid)
            if pid == "openai":
                return {"ok": False, "error": "rate_limit"}
            return {"ok": True, "text": "fallback response"}

        with patch("api.departments.dispatcher._provider_dispatcher") as mock_pd:
            mock_pd.get_provider.return_value = _available_provider()
            mock_pd.invoke.side_effect = invoke

            result = await dispatcher.dispatch(sel, {})

        assert len(calls) >= 2
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_all_providers_fail_returns_error_dict(self):
        dispatcher = DepartmentDispatcher()
        sel = _selection()

        with patch("api.departments.dispatcher._provider_dispatcher") as mock_pd:
            mock_pd.get_provider.return_value = _available_provider()
            mock_pd.invoke = AsyncMock(return_value={"ok": False, "error": "boom"})

            result = await dispatcher.dispatch(sel, {})

        assert result["ok"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_provider_exception_continues_to_next(self):
        dispatcher = DepartmentDispatcher()
        sel = _selection(department_id=DepartmentId.GENERAL, resolved_provider="openai")
        calls = []

        async def invoke(pid, model, payload, **kwargs):
            calls.append(pid)
            if pid == "openai":
                raise RuntimeError("connection refused")
            return {"ok": True, "text": "from fallback"}

        with patch("api.departments.dispatcher._provider_dispatcher") as mock_pd:
            mock_pd.get_provider.return_value = _available_provider()
            mock_pd.invoke.side_effect = invoke

            result = await dispatcher.dispatch(sel, {})

        assert "openai" in calls
        assert result["ok"] is True


# ── list_departments & resolve_provider_id ────────────────────────────────────


class TestHelperMethods:
    def test_list_departments_returns_public_info(self):
        dispatcher = DepartmentDispatcher()
        depts = dispatcher.list_departments()
        assert isinstance(depts, list)
        assert all("department" in d for d in depts)

    def test_resolve_provider_id_valid_department(self):
        dispatcher = DepartmentDispatcher()
        pid = dispatcher.resolve_provider_id("general")
        assert isinstance(pid, str)
        assert len(pid) > 0

    def test_resolve_provider_id_unknown_returns_none(self):
        dispatcher = DepartmentDispatcher()
        result = dispatcher.resolve_provider_id("nonexistent_dept")
        assert result is None

    def test_resolve_provider_id_all_departments(self):
        dispatcher = DepartmentDispatcher()
        for dept_id in ("general", "coding", "reasoning", "creative", "research"):
            pid = dispatcher.resolve_provider_id(dept_id)
            assert pid is not None, f"expected provider for {dept_id}"


# ── dispatch_stream ───────────────────────────────────────────────────────────


class TestDispatchStream:
    @pytest.mark.asyncio
    async def test_stream_yields_status_event(self):
        dispatcher = DepartmentDispatcher()
        sel = _selection()

        async def fake_stream(pid, model, payload, **kwargs):
            yield {"event": "DATA", "content": "hello"}

        with patch("api.departments.dispatcher._provider_dispatcher") as mock_pd:
            mock_pd.get_provider.return_value = _available_provider()
            mock_pd.stream = fake_stream

            chunks = []
            async for chunk in dispatcher.dispatch_stream(sel, {}):
                chunks.append(chunk)

        events = [c.get("event") for c in chunks]
        assert "STATUS" in events

    @pytest.mark.asyncio
    async def test_stream_annotates_chunks_with_department(self):
        dispatcher = DepartmentDispatcher()
        sel = _selection(department_id=DepartmentId.RESEARCH)

        async def fake_stream(pid, model, payload, **kwargs):
            yield {"event": "DATA", "content": "result"}

        with patch("api.departments.dispatcher._provider_dispatcher") as mock_pd:
            mock_pd.get_provider.return_value = _available_provider()
            mock_pd.stream = fake_stream

            chunks = []
            async for chunk in dispatcher.dispatch_stream(sel, {}):
                chunks.append(chunk)

        data_chunks = [c for c in chunks if c.get("event") == "DATA"]
        assert all(c.get("_department") == "research" for c in data_chunks)

    @pytest.mark.asyncio
    async def test_stream_all_fail_yields_error_event(self):
        dispatcher = DepartmentDispatcher()
        sel = _selection()

        with patch("api.departments.dispatcher._provider_dispatcher") as mock_pd:
            mock_pd.get_provider.return_value = _unavailable_provider()

            chunks = []
            async for chunk in dispatcher.dispatch_stream(sel, {}):
                chunks.append(chunk)

        events = [c.get("event") for c in chunks]
        assert "ERROR" in events
