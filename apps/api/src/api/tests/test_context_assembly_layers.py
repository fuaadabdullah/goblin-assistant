import sys
import types
from datetime import datetime, timezone

import pytest

from api.services.context_assembly_service import (
    ContextBudget,
    orchestrator,  # noqa: E402  # test import after path setup
)
from api.services.context_assembly_service import ephemeral_layer as eph
from api.services.context_assembly_service import long_term_layer as ltm
from api.services.context_assembly_service import semantic_layer as sem
from api.services.context_assembly_service import system_layer as sys_layer
from api.services.context_assembly_service import working_memory_layer as wm

# -----------------------------
# Ephemeral layer tests
# -----------------------------


def test_format_ephemeral_memory_empty():
    assert eph.format_ephemeral_memory([]) == ""


def test_format_ephemeral_memory_uses_last_five_messages():
    history = [{"role": "user", "content": f"m{i}"} for i in range(7)]

    content = eph.format_ephemeral_memory(history)

    assert "m0" not in content and "m1" not in content
    assert "m2" in content and "m6" in content


def test_build_ephemeral_summary_empty_and_no_older_messages():
    assert eph.build_ephemeral_summary([]) == ""

    history = [{"role": "user", "content": "only recent"} for _ in range(5)]
    assert eph.build_ephemeral_summary(history) == ""


def test_build_ephemeral_summary_truncates_long_content():
    long_content = "x" * 500
    history = [{"role": "user", "content": "recent"} for _ in range(5)]
    history.insert(0, {"role": "assistant", "content": long_content})

    summary = eph.build_ephemeral_summary(history)

    assert "earlier messages were condensed" in summary
    assert "..." in summary


@pytest.mark.asyncio
async def test_assemble_ephemeral_memory_skips_when_effective_limit_too_small():
    layer = await eph.assemble_ephemeral_memory(
        conversation_history=[{"role": "user", "content": "hi"}],
        remaining_tokens=40,
        budget=ContextBudget(ephemeral_tokens=500),
    )

    assert layer is None


@pytest.mark.asyncio
async def test_assemble_ephemeral_memory_no_truncation(monkeypatch):
    monkeypatch.setattr(eph, "count_tokens", lambda _text: 20)

    layer = await eph.assemble_ephemeral_memory(
        conversation_history=[{"role": "user", "content": "hello"}],
        remaining_tokens=200,
        budget=ContextBudget(ephemeral_tokens=200),
    )

    assert layer is not None
    assert layer.metadata["truncated"] is False
    assert layer.metadata["summary_fallback_applied"] is False


@pytest.mark.asyncio
async def test_assemble_ephemeral_memory_truncates_with_summary_fallback(monkeypatch):
    def _count_tokens(text: str) -> int:
        if text.startswith("## Ephemeral Summary"):
            return 20
        if text.startswith("## Recent Messages"):
            return 200
        return 10

    monkeypatch.setattr(eph, "count_tokens", _count_tokens)
    monkeypatch.setattr(eph, "trim_to_tokens", lambda text, _limit: f"TRIM[{text[:15]}]")

    history = [
        {"role": "user", "content": "very long " * 20},
        {"role": "assistant", "content": "very long " * 20},
        {"role": "user", "content": "very long " * 20},
        {"role": "assistant", "content": "very long " * 20},
        {"role": "user", "content": "very long " * 20},
        {"role": "assistant", "content": "very long " * 20},
    ]

    layer = await eph.assemble_ephemeral_memory(
        conversation_history=history,
        remaining_tokens=120,
        budget=ContextBudget(ephemeral_tokens=120),
    )

    assert layer is not None
    assert layer.metadata["truncated"] is True
    assert layer.metadata["summary_fallback_applied"] is True
    assert "Ephemeral Summary" in layer.content


@pytest.mark.asyncio
async def test_assemble_ephemeral_memory_summary_too_large(monkeypatch):
    def _count_tokens(text: str) -> int:
        if text.startswith("## Ephemeral Summary"):
            return 300
        return 400

    monkeypatch.setattr(eph, "count_tokens", _count_tokens)
    monkeypatch.setattr(eph, "trim_to_tokens", lambda _text, _limit: "summary-trimmed")

    history = [
        {"role": "user", "content": "long " * 50},
        {"role": "assistant", "content": "long " * 50},
        {"role": "user", "content": "long " * 50},
        {"role": "assistant", "content": "long " * 50},
        {"role": "user", "content": "long " * 50},
        {"role": "assistant", "content": "long " * 50},
    ]

    layer = await eph.assemble_ephemeral_memory(
        conversation_history=history,
        remaining_tokens=100,
        budget=ContextBudget(ephemeral_tokens=100),
    )

    assert layer is not None
    assert layer.content == "summary-trimmed"
    assert layer.metadata["summary_fallback_applied"] is True


@pytest.mark.asyncio
async def test_assemble_ephemeral_memory_handles_exceptions(monkeypatch):
    monkeypatch.setattr(eph, "format_ephemeral_memory", lambda _history: 1 / 0)

    layer = await eph.assemble_ephemeral_memory(
        conversation_history=[{"role": "user", "content": "hi"}],
        remaining_tokens=200,
        budget=ContextBudget(ephemeral_tokens=200),
    )

    assert layer is None


# -----------------------------
# Semantic layer tests
# -----------------------------


def test_format_semantic_retrieval_empty():
    assert sem.format_semantic_retrieval([]) == ""


def test_format_semantic_retrieval_with_results():
    content = sem.format_semantic_retrieval(
        [
            {"score": 0.9, "content": "alpha"},
            {"score": 0.4, "content": "beta"},
        ]
    )

    assert "## Relevant Context" in content
    assert "Result 1" in content
    assert "alpha" in content and "beta" in content


@pytest.mark.asyncio
async def test_assemble_semantic_retrieval_skips_for_low_remaining_tokens():
    layer = await sem.assemble_semantic_retrieval(
        query="q",
        user_id="u",
        conversation_id=None,
        remaining_tokens=99,
        correlation_id="corr",
        budget=ContextBudget(),
    )

    assert layer is None


@pytest.mark.asyncio
async def test_assemble_semantic_retrieval_no_results(monkeypatch):
    calls = []

    async def _start_trace(**kwargs):
        calls.append(("start", kwargs))
        return "trace-1"

    async def _end_trace(**kwargs):
        calls.append(("end", kwargs))

    async def _record_tier_breakdown(**kwargs):
        calls.append(("tier", kwargs))

    class _RetrievalService:
        async def retrieve_context(self, **_kwargs):
            return []

    monkeypatch.setattr(sem.retrieval_tracer, "start_trace", _start_trace)
    monkeypatch.setattr(sem.retrieval_tracer, "end_trace", _end_trace)
    monkeypatch.setattr(
        sem.retrieval_tracer,
        "record_tier_breakdown",
        _record_tier_breakdown,
        raising=False,
    )
    monkeypatch.setattr(sem, "_get_retrieval_service", _RetrievalService)

    layer = await sem.assemble_semantic_retrieval(
        query="q",
        user_id="u",
        conversation_id="c",
        remaining_tokens=500,
        correlation_id="corr",
        budget=ContextBudget(),
    )

    assert layer is None
    assert any(c[0] == "start" for c in calls)
    assert any(c[0] == "end" and c[1]["status"] == "no_results" for c in calls)
    assert not any(c[0] == "tier" for c in calls)


@pytest.mark.asyncio
async def test_assemble_semantic_retrieval_success(monkeypatch):
    end_calls = []
    tier_calls = []

    async def _start_trace(**_kwargs):
        return "trace-2"

    async def _end_trace(**kwargs):
        end_calls.append(kwargs)

    async def _record_tier_breakdown(**kwargs):
        tier_calls.append(kwargs)

    class _RetrievalService:
        async def retrieve_context(self, **_kwargs):
            return [{"score": 0.8, "content": "retrieved"}]

    monkeypatch.setattr(sem.retrieval_tracer, "start_trace", _start_trace)
    monkeypatch.setattr(sem.retrieval_tracer, "end_trace", _end_trace)
    monkeypatch.setattr(
        sem.retrieval_tracer,
        "record_tier_breakdown",
        _record_tier_breakdown,
        raising=False,
    )
    monkeypatch.setattr(sem, "_get_retrieval_service", _RetrievalService)
    monkeypatch.setattr(sem, "count_tokens", lambda _text: 40)

    layer = await sem.assemble_semantic_retrieval(
        query="q",
        user_id="u",
        conversation_id="c",
        remaining_tokens=500,
        correlation_id="corr",
        budget=ContextBudget(),
    )

    assert layer is not None
    assert layer.tokens == 40
    assert layer.metadata["hard_stop_applied"] is False
    assert tier_calls and tier_calls[0]["tier"] == "semantic_retrieval"
    assert end_calls and end_calls[0]["status"] == "success"


@pytest.mark.asyncio
async def test_assemble_semantic_retrieval_uses_prompt_cap(monkeypatch):
    captured = {}

    async def _start_trace(**_kwargs):
        return "trace-cap"

    async def _end_trace(**_kwargs):
        return None

    async def _record_tier_breakdown(**_kwargs):
        return None

    class _RetrievalService:
        async def retrieve_context(self, **kwargs):
            captured["k"] = kwargs.get("k")
            return [{"score": 0.8, "content": "retrieved"}]

    monkeypatch.setattr(sem.retrieval_tracer, "start_trace", _start_trace)
    monkeypatch.setattr(sem.retrieval_tracer, "end_trace", _end_trace)
    monkeypatch.setattr(
        sem.retrieval_tracer,
        "record_tier_breakdown",
        _record_tier_breakdown,
        raising=False,
    )
    monkeypatch.setattr(sem, "_get_retrieval_service", _RetrievalService)
    monkeypatch.setattr(sem, "count_tokens", lambda _text: 40)

    layer = await sem.assemble_semantic_retrieval(
        query="q",
        user_id="u",
        conversation_id="c",
        remaining_tokens=500,
        correlation_id="corr",
        budget=ContextBudget(),
    )

    assert layer is not None
    assert captured["k"] == 20


@pytest.mark.asyncio
async def test_assemble_semantic_retrieval_hard_stop(monkeypatch):
    end_calls = []

    async def _start_trace(**_kwargs):
        return "trace-3"

    async def _end_trace(**kwargs):
        end_calls.append(kwargs)

    async def _record_tier_breakdown(**_kwargs):
        return None

    class _RetrievalService:
        async def retrieve_context(self, **_kwargs):
            return [{"score": 0.8, "content": "retrieved"}]

    monkeypatch.setattr(sem.retrieval_tracer, "start_trace", _start_trace)
    monkeypatch.setattr(sem.retrieval_tracer, "end_trace", _end_trace)
    monkeypatch.setattr(
        sem.retrieval_tracer,
        "record_tier_breakdown",
        _record_tier_breakdown,
        raising=False,
    )
    monkeypatch.setattr(sem, "_get_retrieval_service", _RetrievalService)
    monkeypatch.setattr(sem, "count_tokens", lambda _text: 1000)
    monkeypatch.setattr(sem, "trim_to_tokens", lambda _text, _limit: "trimmed")

    layer = await sem.assemble_semantic_retrieval(
        query="q",
        user_id="u",
        conversation_id="c",
        remaining_tokens=150,
        correlation_id="corr",
        budget=ContextBudget(),
    )

    assert layer is not None
    assert layer.content == "trimmed"
    assert layer.tokens == 150
    assert layer.metadata["hard_stop_applied"] is True
    assert end_calls and end_calls[0]["hard_stop_applied"] is True


@pytest.mark.asyncio
async def test_assemble_semantic_retrieval_exception_ends_trace(monkeypatch):
    end_calls = []

    async def _start_trace(**_kwargs):
        return "trace-4"

    async def _end_trace(**kwargs):
        end_calls.append(kwargs)

    async def _record_tier_breakdown(**_kwargs):
        return None

    class _RetrievalService:
        async def retrieve_context(self, **_kwargs):
            raise RuntimeError("retrieval failed")

    monkeypatch.setattr(sem.retrieval_tracer, "start_trace", _start_trace)
    monkeypatch.setattr(sem.retrieval_tracer, "end_trace", _end_trace)
    monkeypatch.setattr(
        sem.retrieval_tracer,
        "record_tier_breakdown",
        _record_tier_breakdown,
        raising=False,
    )
    monkeypatch.setattr(sem, "_get_retrieval_service", _RetrievalService)

    layer = await sem.assemble_semantic_retrieval(
        query="q",
        user_id="u",
        conversation_id="c",
        remaining_tokens=200,
        correlation_id="corr",
        budget=ContextBudget(),
    )

    assert layer is None
    assert end_calls and end_calls[0]["status"] == "error"
    assert "retrieval failed" in end_calls[0]["error"]


# -----------------------------
# Long-term & working memory retrieval helper tests
# -----------------------------


class _FakeQuery:
    def join(self, *_args, **_kwargs):
        return self

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self._rows


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows

    async def execute(self, _stmt):
        return _FakeResult(self._rows)


class _FakeSessionContext:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_get_long_term_memory_facts_success(monkeypatch):
    now = datetime.now(timezone.utc)
    rows = [types.SimpleNamespace(fact_text="fact", category="pref", created_at=now)]

    monkeypatch.setitem(
        sys.modules,
        "sqlalchemy",
        types.SimpleNamespace(select=lambda _model: _FakeQuery()),
    )
    monkeypatch.setattr(
        ltm,
        "get_readonly_db_context",
        lambda: _FakeSessionContext(_FakeSession(rows)),
    )

    facts = await ltm.get_long_term_memory_facts("u1")

    assert facts == [
        {
            "content": "fact",
            "category": "pref",
            "memory_type": "pref",
            "created_at": now.isoformat(),
        }
    ]


@pytest.mark.asyncio
async def test_get_long_term_memory_facts_error(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "sqlalchemy",
        types.SimpleNamespace(
            select=lambda _model: (_ for _ in ()).throw(RuntimeError("bad select"))
        ),
    )

    facts = await ltm.get_long_term_memory_facts("u1")

    assert facts == []


def test_format_long_term_memory_empty_and_non_empty():
    assert ltm.format_long_term_memory([]) == ""

    formatted = ltm.format_long_term_memory([{"content": "likes tea", "category": "prefs"}])
    assert "User Preferences" in formatted
    assert "likes tea" in formatted


# -----------------------------
# _cluster_sentence and build_session_memory_pack tests
# -----------------------------


def test_cluster_sentence_project():
    """Test clustering for project entity type."""
    result = ltm._cluster_sentence("project", "my-project", ["task1", "task2"])
    assert "my-project" in result
    assert "task1" in result


def test_cluster_sentence_preference():
    """Test clustering for preference entity type."""
    result = ltm._cluster_sentence("preference", "dark-mode", ["enabled"])
    assert "Prefers dark-mode" in result


def test_cluster_sentence_decision():
    """Test clustering for decision entity type."""
    result = ltm._cluster_sentence("decision", "general", ["decided on x"])
    assert "Decided:" in result


def test_cluster_sentence_other_with_entity():
    """Test clustering for other entity types with entity value."""
    result = ltm._cluster_sentence("tool", "vscode", ["used for editing"])
    assert "vscode" in result


def test_cluster_sentence_other_without_entity():
    """Test clustering for other entity types without entity value."""
    result = ltm._cluster_sentence("tool", "general", ["used for editing"])
    assert result.endswith(".")


def test_build_session_memory_pack_empty():
    """Test session pack with empty facts returns empty string."""
    assert ltm.build_session_memory_pack([]) == ""


def test_build_session_memory_pack_single_cluster():
    """Test session pack with single cluster of facts."""
    facts = [{"content": "like coffee", "memory_type": "preference", "entity_refs": None}]
    result = ltm.build_session_memory_pack(facts)
    assert "User context:" in result
    assert "like coffee" in result


def test_build_session_memory_pack_multiple_clusters():
    """Test session pack with multiple clusters grouped by entity."""
    facts = [
        {
            "content": "task1",
            "memory_type": "project",
            "entity_refs": [{"type": "project", "value": "goblin"}],
        },
        {
            "content": "task2",
            "memory_type": "project",
            "entity_refs": [{"type": "project", "value": "goblin"}],
        },
        {
            "content": "task3",
            "memory_type": "preference",
            "entity_refs": [{"type": "preference", "value": "theme"}],
        },
    ]
    result = ltm.build_session_memory_pack(facts)
    assert "User context:" in result
    assert "goblin" in result
    assert "theme" in result


def test_build_session_memory_pack_entity_refs_missing():
    """Test session pack falls back when entity_refs missing."""
    facts = [{"content": "some fact", "memory_type": "general"}]
    result = ltm.build_session_memory_pack(facts)
    assert "User context:" in result
    # Falls back to using memory_type as entity type
    assert "some fact" in result


def test_build_session_memory_pack_entity_refs_not_list():
    """Test session pack handles entity_refs not being a list."""
    facts = [{"content": "some fact", "memory_type": "general", "entity_refs": "not-a-list"}]
    result = ltm.build_session_memory_pack(facts)
    assert "User context:" in result
    # Falls back to using memory_type as entity type
    assert "some fact" in result


@pytest.mark.asyncio
async def test_assemble_long_term_memory_paths(monkeypatch):
    budget = ContextBudget(long_term_tokens=100)

    layer = await ltm.assemble_long_term_memory("u", remaining_tokens=50, budget=budget)
    assert layer is None

    async def _no_facts(_user_id):
        return []

    monkeypatch.setattr(ltm, "get_long_term_memory_facts", _no_facts)
    layer = await ltm.assemble_long_term_memory("u", remaining_tokens=200, budget=budget)
    assert layer is None

    async def _facts(_user_id):
        return [{"content": "x", "category": "c"}]

    monkeypatch.setattr(ltm, "get_long_term_memory_facts", _facts)
    monkeypatch.setattr(ltm, "count_tokens", lambda _text: 150)
    monkeypatch.setattr(ltm, "trim_to_tokens", lambda _text, _limit: "trimmed-long-term")

    layer = await ltm.assemble_long_term_memory("u", remaining_tokens=200, budget=budget)
    assert layer is not None
    assert layer.content == "trimmed-long-term"
    assert layer.tokens == 100

    async def _boom(_user_id):
        raise RuntimeError("boom")

    monkeypatch.setattr(ltm, "get_long_term_memory_facts", _boom)
    layer = await ltm.assemble_long_term_memory("u", remaining_tokens=200, budget=budget)
    assert layer is None


@pytest.mark.asyncio
async def test_assemble_long_term_memory_compression_level(monkeypatch):
    """Test compression level 3 triggers session pack."""
    budget = ContextBudget(long_term_tokens=100)

    async def _facts(_user_id):
        return [{"content": "fact", "category": "pref", "entity_refs": None}]

    monkeypatch.setattr(ltm, "get_long_term_memory_facts", _facts)
    monkeypatch.setattr(ltm, "count_tokens", lambda _text: 50)
    monkeypatch.setattr(ltm, "trim_to_tokens", lambda _text, _limit: "trimmed")

    # Use compression_level=3 to trigger session pack
    layer = await ltm.assemble_long_term_memory(
        "u", remaining_tokens=500, budget=budget, compression_level=3
    )
    assert layer is not None
    assert layer.metadata["compression_level"] == 3


@pytest.mark.asyncio
async def test_assemble_long_term_memory_tight_budget_triggers_level3(monkeypatch):
    """Test tight budget triggers level 3 automatically."""
    budget = ContextBudget(long_term_tokens=400)

    async def _many_facts(_user_id):
        return [{"content": "x" * 100, "category": "c"} for _ in range(10)]

    monkeypatch.setattr(ltm, "get_long_term_memory_facts", _many_facts)
    monkeypatch.setattr(ltm, "count_tokens", lambda _text: 500)
    monkeypatch.setattr(ltm, "trim_to_tokens", lambda _text, _limit: "trimmed")

    # Need remaining_tokens >= budget.long_term_tokens for layer to be assembled
    layer = await ltm.assemble_long_term_memory("u", remaining_tokens=500, budget=budget)
    assert layer is not None
    # level 3 is triggered when remaining_tokens < budget.long_term_tokens * 2
    assert layer.metadata["compression_level"] == 3


@pytest.mark.asyncio
async def test_get_working_memory_summaries_success(monkeypatch):
    now = datetime.now(timezone.utc)
    rows = [types.SimpleNamespace(summary_text="summary", created_at=now)]
    fake_model = types.SimpleNamespace(
        user_id=object(),
        conversation_id=object(),
        created_at=types.SimpleNamespace(desc=lambda: None),
    )

    monkeypatch.setitem(
        sys.modules,
        "sqlalchemy",
        types.SimpleNamespace(select=lambda _model: _FakeQuery()),
    )
    monkeypatch.setattr(
        wm,
        "get_readonly_db_context",
        lambda: _FakeSessionContext(_FakeSession(rows)),
    )
    monkeypatch.setattr(wm, "ConversationSummaryModel", fake_model)

    summaries = await wm.get_working_memory_summaries("u1", "c1")

    assert summaries == [{"content": "summary", "created_at": now.isoformat()}]


@pytest.mark.asyncio
async def test_get_working_memory_summaries_error(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "sqlalchemy",
        types.SimpleNamespace(
            select=lambda _model: (_ for _ in ()).throw(RuntimeError("bad select"))
        ),
    )

    summaries = await wm.get_working_memory_summaries("u1", "c1")

    assert summaries == []


def test_format_working_memory_empty_and_non_empty():
    assert wm.format_working_memory([]) == ""

    formatted = wm.format_working_memory([{"content": "in progress"}])
    assert "Current Conversation Context" in formatted
    assert "in progress" in formatted


@pytest.mark.asyncio
async def test_assemble_working_memory_paths(monkeypatch):
    budget = ContextBudget(working_memory_tokens=100)

    layer = await wm.assemble_working_memory("u", "c", remaining_tokens=50, budget=budget)
    assert layer is None

    async def _no_summaries(_user_id, _conversation_id):
        return []

    monkeypatch.setattr(wm, "get_working_memory_summaries", _no_summaries)
    layer = await wm.assemble_working_memory("u", "c", remaining_tokens=200, budget=budget)
    assert layer is None

    async def _summaries(_user_id, _conversation_id):
        return [{"content": "sum"}]

    monkeypatch.setattr(wm, "get_working_memory_summaries", _summaries)
    monkeypatch.setattr(wm, "count_tokens", lambda _text: 150)
    monkeypatch.setattr(wm, "trim_to_tokens", lambda _text, _limit: "trimmed-working")

    layer = await wm.assemble_working_memory("u", "c", remaining_tokens=200, budget=budget)
    assert layer is not None
    assert layer.content == "trimmed-working"
    assert layer.tokens == 100

    async def _boom(_user_id, _conversation_id):
        raise RuntimeError("boom")

    monkeypatch.setattr(wm, "get_working_memory_summaries", _boom)
    layer = await wm.assemble_working_memory("u", "c", remaining_tokens=200, budget=budget)
    assert layer is None


# -----------------------------
# System layer tests
# -----------------------------


class _FixedDatetime(datetime):
    @classmethod
    def now(cls, _tz=None):
        return datetime(2026, 7, 17, 12, 34, 56, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_assemble_system_layer_budget_gate():
    layer = await sys_layer.assemble_system_layer(
        remaining_tokens=50,
        budget=ContextBudget(system_tokens=100),
    )
    assert layer is None


@pytest.mark.asyncio
async def test_assemble_system_layer_normal_and_trim(monkeypatch):
    monkeypatch.setattr(sys_layer, "count_tokens", lambda _text: 80)

    normal = await sys_layer.assemble_system_layer(
        remaining_tokens=200,
        budget=ContextBudget(system_tokens=100),
    )
    assert normal is not None
    assert normal.tokens == 80
    assert normal.metadata["fixed_cost"] is True

    monkeypatch.setattr(sys_layer, "count_tokens", lambda _text: 120)
    monkeypatch.setattr(sys_layer, "trim_to_tokens", lambda _text, _limit: "trimmed-system")

    trimmed = await sys_layer.assemble_system_layer(
        remaining_tokens=200,
        budget=ContextBudget(system_tokens=100),
    )
    assert trimmed is not None
    assert trimmed.content == "trimmed-system"
    assert trimmed.tokens == 100


@pytest.mark.asyncio
async def test_assemble_system_layer_trims_after_runtime_context(monkeypatch):
    captured = {}

    def _trim(text: str, limit: int) -> str:
        captured["text"] = text
        captured["limit"] = limit
        return "trimmed-system"

    monkeypatch.setattr(sys_layer, "datetime", _FixedDatetime)
    monkeypatch.setattr(sys_layer, "count_tokens", lambda _text: 120)
    monkeypatch.setattr(sys_layer, "trim_to_tokens", _trim)

    trimmed = await sys_layer.assemble_system_layer(
        remaining_tokens=200,
        budget=ContextBudget(system_tokens=100),
    )

    assert trimmed is not None
    assert trimmed.content == "trimmed-system"
    assert trimmed.tokens == 100
    assert captured["limit"] == 100
    assert captured["text"].startswith(
        "Runtime context:\nCurrent UTC date/time: 2026-07-17T12:34:56+00:00"
    )


# -----------------------------
# build_default_system_message test
# -----------------------------


@pytest.mark.asyncio
async def test_build_default_system_message_success(monkeypatch):
    """Test build_default_system_message returns system message dict."""
    monkeypatch.setattr(sys_layer, "count_tokens", lambda _text: 50)

    result = await sys_layer.build_default_system_message()

    assert result is not None
    assert result["role"] == "system"
    assert len(result["content"]) > 0


@pytest.mark.asyncio
async def test_build_default_system_message_returns_none_on_failure(monkeypatch):
    """Test build_default_system_message returns None when assembly fails."""

    async def _raise_on_layer(*args, **kwargs):
        return None

    monkeypatch.setattr(sys_layer, "assemble_system_layer", _raise_on_layer)

    result = await sys_layer.build_default_system_message()

    assert result is None


# -----------------------------
# _expand_query_for_intent tests
# -----------------------------


def test_expand_query_for_intent_none_confidence():
    """Test intent with None confidence returns original query."""

    class MockIntent:
        confidence = 0.0
        label = None

    result = orchestrator._expand_query_for_intent("test query", MockIntent())
    assert result == "test query"


def test_expand_query_for_intent_low_confidence():
    """Test intent with low confidence returns original query."""

    class MockIntent:
        confidence = 0.5
        label = None

    result = orchestrator._expand_query_for_intent("test query", MockIntent())
    assert result == "test query"


def test_expand_query_for_intent_high_confidence():
    """Test intent with high confidence appends suffix."""

    class MockLabel:
        value = "coding"

    class MockIntent:
        confidence = 0.8
        label = MockLabel()

    result = orchestrator._expand_query_for_intent("fix bug", MockIntent())
    assert "code implementation technical" in result


def test_expand_query_for_intent_missing_label():
    """Test intent with missing label attribute returns original query."""

    class MockIntent:
        confidence = 0.8
        label = None

    result = orchestrator._expand_query_for_intent("test query", MockIntent())
    assert result == "test query"


def test_expand_query_for_intent_unknown_label():
    """Test intent with unknown label type returns original query."""

    class MockLabel:
        value = "unknown_type"

    class MockIntent:
        confidence = 0.8
        label = MockLabel()

    result = orchestrator._expand_query_for_intent("test query", MockIntent())
    assert result == "test query"


def test_expand_query_for_intent_exception_handling():
    """Test intent that raises exception during processing returns original query."""

    class BadIntent:
        def __getattr__(self, name):
            raise RuntimeError("bad intent")

    result = orchestrator._expand_query_for_intent("test query", BadIntent())
    assert result == "test query"
