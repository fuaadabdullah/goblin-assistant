"""Tests for services/feedback_service.py — FeedbackService and data classes."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.services.feedback_service import (
    FeedbackContext,
    FeedbackEvent,
    FeedbackService,
    FeedbackSignal,
    FeedbackStats,
    feedback_service,
)

# ── FeedbackSignal constants ──────────────────────────────────────────────────


class TestFeedbackSignal:
    def test_all_eight_signals_exist(self):
        signals = {
            FeedbackSignal.THUMBS_UP,
            FeedbackSignal.THUMBS_DOWN,
            FeedbackSignal.REGENERATE,
            FeedbackSignal.DELETE,
            FeedbackSignal.CONTINUE,
            FeedbackSignal.PROVIDER_SWITCH,
            FeedbackSignal.MODEL_SWITCH,
            FeedbackSignal.COPY,
        }
        assert len(signals) == 8

    def test_thumbs_up_value(self):
        assert FeedbackSignal.THUMBS_UP == "thumbs_up"

    def test_thumbs_down_value(self):
        assert FeedbackSignal.THUMBS_DOWN == "thumbs_down"

    def test_copy_value(self):
        assert FeedbackSignal.COPY == "copy"

    def test_all_values_are_strings(self):
        for attr in (
            "THUMBS_UP",
            "THUMBS_DOWN",
            "REGENERATE",
            "DELETE",
            "CONTINUE",
            "PROVIDER_SWITCH",
            "MODEL_SWITCH",
            "COPY",
        ):
            assert isinstance(getattr(FeedbackSignal, attr), str)


# ── FeedbackContext dataclass ─────────────────────────────────────────────────


class TestFeedbackContext:
    def test_construction_with_required_fields(self):
        ctx = FeedbackContext(
            user_id="user-1",
            conversation_id="conv-1",
            message_id="msg-1",
        )
        assert ctx.user_id == "user-1"
        assert ctx.conversation_id == "conv-1"
        assert ctx.message_id == "msg-1"

    def test_optional_fields_default_to_none(self):
        ctx = FeedbackContext(user_id="u", conversation_id="c", message_id="m")
        assert ctx.request_id is None
        assert ctx.department is None
        assert ctx.provider is None
        assert ctx.model is None
        assert ctx.task_type is None
        assert ctx.intent_label is None
        assert ctx.complexity_score is None
        assert ctx.previous_provider is None
        assert ctx.previous_model is None

    def test_all_fields_settable(self):
        ctx = FeedbackContext(
            user_id="u",
            conversation_id="c",
            message_id="m",
            request_id="req-1",
            department="coding",
            provider="anthropic",
            model="claude-sonnet-4-6",
            task_type="code_review",
            intent_label="coding",
            complexity_score=0.8,
            previous_provider="openai",
            previous_model="gpt-4o",
        )
        assert ctx.department == "coding"
        assert ctx.complexity_score == pytest.approx(0.8)


# ── FeedbackEvent dataclass ───────────────────────────────────────────────────


class TestFeedbackEvent:
    def test_construction_with_signal(self):
        event = FeedbackEvent(signal=FeedbackSignal.THUMBS_UP)
        assert event.signal == "thumbs_up"

    def test_rating_defaults_to_none(self):
        event = FeedbackEvent(signal=FeedbackSignal.COPY)
        assert event.rating is None

    def test_weight_defaults_to_one(self):
        event = FeedbackEvent(signal=FeedbackSignal.DELETE)
        assert event.weight == pytest.approx(1.0)

    def test_metadata_defaults_to_empty_dict(self):
        event = FeedbackEvent(signal=FeedbackSignal.REGENERATE)
        assert event.metadata == {}

    def test_with_rating_and_metadata(self):
        event = FeedbackEvent(
            signal=FeedbackSignal.THUMBS_DOWN,
            rating=-1,
            weight=0.9,
            metadata={"reason": "bad response"},
        )
        assert event.rating == -1
        assert event.weight == pytest.approx(0.9)
        assert event.metadata["reason"] == "bad response"


# ── FeedbackStats dataclass ───────────────────────────────────────────────────


class TestFeedbackStats:
    def test_all_counts_default_to_zero(self):
        stats = FeedbackStats()
        assert stats.total_events == 0
        assert stats.thumbs_up_count == 0
        assert stats.thumbs_down_count == 0
        assert stats.regenerate_count == 0
        assert stats.delete_count == 0
        assert stats.continue_count == 0
        assert stats.copy_count == 0
        assert stats.provider_switch_count == 0
        assert stats.model_switch_count == 0

    def test_thumbs_up_rate_defaults_to_zero(self):
        stats = FeedbackStats()
        assert stats.thumbs_up_rate == pytest.approx(0.0)

    def test_dicts_default_to_empty(self):
        stats = FeedbackStats()
        assert stats.by_department == {}
        assert stats.by_provider == {}
        assert stats.recent_events == []


# ── FeedbackService.record_explicit_rating ────────────────────────────────────


def _make_context(**kwargs):
    defaults = dict(user_id="user-1", conversation_id="conv-1", message_id="msg-1")
    defaults.update(kwargs)
    return FeedbackContext(**defaults)


def _db_patch():
    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    return mock_db


class TestRecordExplicitRating:
    @pytest.mark.asyncio
    async def test_thumbs_up_rating(self):
        svc = FeedbackService()
        ctx = _make_context()

        with patch.dict(
            "sys.modules",
            {
                "api.storage.database": MagicMock(get_db=MagicMock(return_value=_db_patch())),
                "api.storage.feedback_models": MagicMock(
                    FeedbackEventModel=MagicMock(return_value=MagicMock(event_id="evt-1")),
                    MessageOutcomeModel=MagicMock(return_value=MagicMock()),
                ),
                "api.storage.models": MagicMock(
                    DomainEventModel=MagicMock(return_value=MagicMock())
                ),
                "api.services.outcome_scorer": MagicMock(
                    outcome_scorer=MagicMock(points_for=MagicMock(return_value=5))
                ),
            },
        ):
            await svc.record_explicit_rating(ctx, rating=1)

    @pytest.mark.asyncio
    async def test_thumbs_down_rating(self):
        svc = FeedbackService()
        ctx = _make_context()

        with patch.dict(
            "sys.modules",
            {
                "api.storage.database": MagicMock(get_db=MagicMock(return_value=_db_patch())),
                "api.storage.feedback_models": MagicMock(
                    FeedbackEventModel=MagicMock(return_value=MagicMock(event_id="evt-2")),
                    MessageOutcomeModel=MagicMock(return_value=MagicMock()),
                ),
                "api.storage.models": MagicMock(
                    DomainEventModel=MagicMock(return_value=MagicMock())
                ),
                "api.services.outcome_scorer": MagicMock(
                    outcome_scorer=MagicMock(points_for=MagicMock(return_value=-5))
                ),
            },
        ):
            await svc.record_explicit_rating(ctx, rating=-1)

    @pytest.mark.asyncio
    async def test_db_failure_does_not_raise(self):
        svc = FeedbackService()
        ctx = _make_context()

        with patch.dict(
            "sys.modules",
            {
                "api.storage.database": MagicMock(
                    get_db=MagicMock(side_effect=RuntimeError("db down"))
                ),
                "api.storage.feedback_models": MagicMock(
                    FeedbackEventModel=MagicMock(),
                    MessageOutcomeModel=MagicMock(),
                ),
                "api.storage.models": MagicMock(DomainEventModel=MagicMock()),
                "api.services.outcome_scorer": MagicMock(
                    outcome_scorer=MagicMock(points_for=MagicMock(return_value=0))
                ),
            },
        ):
            # Should not raise — fire-and-forget design
            await svc.record_explicit_rating(ctx, rating=1)


# ── FeedbackService implicit signal methods ───────────────────────────────────


def _patch_db_and_scorer():
    return patch.dict(
        "sys.modules",
        {
            "api.storage.database": MagicMock(get_db=MagicMock(return_value=_db_patch())),
            "api.storage.feedback_models": MagicMock(
                FeedbackEventModel=MagicMock(return_value=MagicMock(event_id="evt-x")),
                MessageOutcomeModel=MagicMock(return_value=MagicMock()),
            ),
            "api.storage.models": MagicMock(DomainEventModel=MagicMock(return_value=MagicMock())),
            "api.services.outcome_scorer": MagicMock(
                outcome_scorer=MagicMock(points_for=MagicMock(return_value=0))
            ),
        },
    )


class TestImplicitSignals:
    @pytest.mark.asyncio
    async def test_record_regenerate_does_not_raise(self):
        svc = FeedbackService()
        with _patch_db_and_scorer():
            await svc.record_regenerate(_make_context())

    @pytest.mark.asyncio
    async def test_record_delete_does_not_raise(self):
        svc = FeedbackService()
        with _patch_db_and_scorer():
            await svc.record_delete(_make_context())

    @pytest.mark.asyncio
    async def test_record_copied_does_not_raise(self):
        svc = FeedbackService()
        with _patch_db_and_scorer():
            await svc.record_copied(_make_context())

    @pytest.mark.asyncio
    async def test_record_conversation_continued_does_not_raise(self):
        svc = FeedbackService()
        with _patch_db_and_scorer():
            await svc.record_conversation_continued(_make_context(), next_message_id="msg-2")

    @pytest.mark.asyncio
    async def test_record_provider_switch_different_provider_is_provider_switch(self):
        svc = FeedbackService()
        ctx = _make_context(provider="openai")
        captured_signal = {}

        async def capture_persist(event):
            captured_signal["signal"] = event.signal

        svc._persist_event = capture_persist
        svc._update_message_outcome = AsyncMock()

        await svc.record_provider_switch(ctx, new_provider="anthropic")

        assert captured_signal["signal"] == FeedbackSignal.PROVIDER_SWITCH

    @pytest.mark.asyncio
    async def test_record_provider_switch_same_provider_is_model_switch(self):
        svc = FeedbackService()
        ctx = _make_context(provider="openai", model="gpt-4o")
        captured_signal = {}

        async def capture_persist(event):
            captured_signal["signal"] = event.signal

        svc._persist_event = capture_persist
        svc._update_message_outcome = AsyncMock()

        await svc.record_provider_switch(ctx, new_provider="openai", new_model="gpt-4o-mini")

        assert captured_signal["signal"] == FeedbackSignal.MODEL_SWITCH


# ── FeedbackService.get_feedback_stats ───────────────────────────────────────


class _ColMock:
    """Pure-Python column mock that supports comparison operators.

    MagicMock subclasses cannot override __ge__/__le__ in Python 3.13+ because the
    MagicMock metaclass overrides magic methods via slot machinery. A plain class avoids this.
    """

    def __ge__(self, other):
        return MagicMock()

    def __le__(self, other):
        return MagicMock()

    def __gt__(self, other):
        return MagicMock()

    def __lt__(self, other):
        return MagicMock()

    def isnot(self, other):
        return MagicMock()

    def label(self, name):
        return MagicMock()

    def __hash__(self):
        return id(self)


def _make_feedback_model_mock():
    """FeedbackEventModel mock where column attributes support SQLAlchemy-style comparison ops."""
    model = MagicMock()
    model.created_at = _ColMock()
    model.signal = _ColMock()
    model.department = _ColMock()
    model.provider = _ColMock()
    return model


class TestGetFeedbackStats:
    def _mock_db_with_counts(self, signal_rows, dept_rows=None, prov_rows=None):
        counts_result = MagicMock()
        counts_result.all.return_value = signal_rows

        dept_result = MagicMock()
        dept_result.all.return_value = dept_rows or []

        prov_result = MagicMock()
        prov_result.all.return_value = prov_rows or []

        recent_result = MagicMock()
        recent_result.scalars.return_value.all.return_value = []

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(
            side_effect=[counts_result, dept_result, prov_result, recent_result]
        )
        return mock_db

    def _stats_patches(self, feedback_model_mock=None):
        """Context managers to bypass SQLAlchemy query building in get_feedback_stats."""
        model = feedback_model_mock or _make_feedback_model_mock()
        return (
            patch("api.services.feedback_service.select", return_value=MagicMock()),
            patch("api.services.feedback_service.func", MagicMock()),
            patch.dict(
                "sys.modules",
                {
                    "api.storage.feedback_models": MagicMock(FeedbackEventModel=model),
                },
            ),
        )

    @pytest.mark.asyncio
    async def test_empty_db_returns_zero_stats(self):
        svc = FeedbackService()
        mock_db = self._mock_db_with_counts([])
        p1, p2, p3 = self._stats_patches()
        with p1, p2, p3:
            stats = await svc.get_feedback_stats(mock_db, days=7)
        assert stats.total_events == 0
        assert stats.thumbs_up_count == 0

    @pytest.mark.asyncio
    async def test_thumbs_up_count_populated(self):
        svc = FeedbackService()
        signal_rows = [
            ("thumbs_up", 10),
            ("thumbs_down", 3),
            ("regenerate", 2),
            ("copy", 5),
        ]
        mock_db = self._mock_db_with_counts(signal_rows)
        p1, p2, p3 = self._stats_patches()
        with p1, p2, p3:
            stats = await svc.get_feedback_stats(mock_db, days=7)
        assert stats.thumbs_up_count == 10
        assert stats.thumbs_down_count == 3
        assert stats.regenerate_count == 2
        assert stats.copy_count == 5
        assert stats.total_events == 20

    @pytest.mark.asyncio
    async def test_thumbs_up_rate_computed(self):
        svc = FeedbackService()
        mock_db = self._mock_db_with_counts([("thumbs_up", 8), ("thumbs_down", 2)])
        p1, p2, p3 = self._stats_patches()
        with p1, p2, p3:
            stats = await svc.get_feedback_stats(mock_db, days=7)
        assert stats.thumbs_up_rate == pytest.approx(0.8)

    @pytest.mark.asyncio
    async def test_all_signal_types_mapped(self):
        svc = FeedbackService()
        signal_rows = [
            ("thumbs_up", 1),
            ("thumbs_down", 2),
            ("regenerate", 3),
            ("delete", 4),
            ("continue", 5),
            ("copy", 6),
            ("provider_switch", 7),
            ("model_switch", 8),
        ]
        mock_db = self._mock_db_with_counts(signal_rows)
        p1, p2, p3 = self._stats_patches()
        with p1, p2, p3:
            stats = await svc.get_feedback_stats(mock_db, days=7)
        assert stats.delete_count == 4
        assert stats.continue_count == 5
        assert stats.provider_switch_count == 7
        assert stats.model_switch_count == 8

    @pytest.mark.asyncio
    async def test_db_exception_returns_empty_stats(self):
        svc = FeedbackService()
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=RuntimeError("query failed"))
        p1, p2, p3 = self._stats_patches()
        with p1, p2, p3:
            stats = await svc.get_feedback_stats(mock_db, days=7)
        assert isinstance(stats, FeedbackStats)
        assert stats.total_events == 0


# ── Singleton ─────────────────────────────────────────────────────────────────


def test_feedback_service_singleton_exists():
    assert feedback_service is not None
    assert isinstance(feedback_service, FeedbackService)
