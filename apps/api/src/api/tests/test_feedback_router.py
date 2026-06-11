"""Tests for routing/feedback_router.py — POST /routing/feedback and GET /feedback/stats."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routing.feedback_router import (
    FeedbackResponse,
    FeedbackStatsResponse,
    router,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _no_supabase(monkeypatch=None):
    """Patch _lookup_routing_event to return (None, None, None) — no Supabase dep."""
    return patch(
        "api.routing.feedback_router._lookup_routing_event",
        new_callable=AsyncMock,
        return_value=(None, None, None),
    )


# ── FeedbackRequest validation ────────────────────────────────────────────────


class TestFeedbackRequestValidation:
    def test_valid_thumbs_up(self, client):
        with _no_supabase():
            resp = client.post("/routing/feedback", json={"request_id": "req-1", "rating": 1})
        assert resp.status_code == 200

    def test_valid_thumbs_down(self, client):
        with _no_supabase():
            resp = client.post("/routing/feedback", json={"request_id": "req-1", "rating": -1})
        assert resp.status_code == 200

    def test_rating_zero_rejected(self, client):
        resp = client.post("/routing/feedback", json={"request_id": "req-1", "rating": 0})
        assert resp.status_code == 422

    def test_rating_two_rejected(self, client):
        resp = client.post("/routing/feedback", json={"request_id": "req-1", "rating": 2})
        assert resp.status_code == 422

    def test_rating_none_accepted(self, client):
        with _no_supabase():
            resp = client.post("/routing/feedback", json={"request_id": "req-1", "signal": "copy"})
        assert resp.status_code == 200

    def test_missing_request_id_rejected(self, client):
        resp = client.post("/routing/feedback", json={"rating": 1})
        assert resp.status_code == 422

    def test_all_optional_fields_omitted(self, client):
        with _no_supabase():
            resp = client.post("/routing/feedback", json={"request_id": "req-only"})
        assert resp.status_code == 200


# ── POST /routing/feedback — basic response ───────────────────────────────────


class TestSubmitFeedback:
    def test_returns_ok_true(self, client):
        with _no_supabase():
            resp = client.post(
                "/routing/feedback",
                json={
                    "request_id": "req-1",
                    "rating": 1,
                    "provider_id": "openai",
                    "task_type": "chat",
                },
            )
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    def test_signal_copy_no_rating_still_returns_ok(self, client):
        with _no_supabase():
            resp = client.post(
                "/routing/feedback",
                json={"request_id": "req-1", "signal": "copy", "message_id": "msg-1"},
            )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_signal_regenerate_returns_ok(self, client):
        with _no_supabase():
            resp = client.post(
                "/routing/feedback",
                json={"request_id": "req-1", "signal": "regenerate", "message_id": "msg-1"},
            )
        assert resp.status_code == 200

    def test_signal_delete_returns_ok(self, client):
        with _no_supabase():
            resp = client.post(
                "/routing/feedback",
                json={"request_id": "req-1", "signal": "delete", "message_id": "msg-1"},
            )
        assert resp.status_code == 200

    def test_internal_exception_still_returns_ok(self, client):
        with (
            _no_supabase(),
            patch.dict(
                "sys.modules",
                {
                    "api.routing.ml_router": MagicMock(
                        bandit_cache=MagicMock(
                            update=MagicMock(side_effect=RuntimeError("bandit down"))
                        ),
                        _fire_bandit_state_upsert=MagicMock(),
                    ),
                },
            ),
        ):
            resp = client.post(
                "/routing/feedback",
                json={
                    "request_id": "req-1",
                    "rating": 1,
                    "provider_id": "openai",
                    "task_type": "chat",
                },
            )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


# ── POST /routing/feedback — bandit update path ───────────────────────────────


class TestBanditUpdatePath:
    def test_rating_signal_updates_bandit(self, client):
        bandit_update = MagicMock(return_value=MagicMock(alpha=2.0, beta=1.0))

        with (
            _no_supabase(),
            patch.dict(
                "sys.modules",
                {
                    "api.routing.ml_router": MagicMock(
                        bandit_cache=MagicMock(update=bandit_update),
                        _fire_bandit_state_upsert=MagicMock(),
                    ),
                    "api.routing.feature_router": MagicMock(
                        feature_router=MagicMock(
                            record_outcome_by_request_id=MagicMock(return_value=True)
                        )
                    ),
                },
            ),
        ):
            client.post(
                "/routing/feedback",
                json={
                    "request_id": "req-1",
                    "rating": 1,
                    "provider_id": "openai",
                    "task_type": "chat",
                },
            )

        bandit_update.assert_called_once()
        call_kwargs = bandit_update.call_args
        assert call_kwargs.kwargs.get("rating") == 1

    def test_no_rating_skips_bandit(self, client):
        bandit_update = MagicMock()

        with (
            _no_supabase(),
            patch.dict(
                "sys.modules",
                {
                    "api.routing.ml_router": MagicMock(
                        bandit_cache=MagicMock(update=bandit_update),
                        _fire_bandit_state_upsert=MagicMock(),
                    ),
                },
            ),
        ):
            client.post(
                "/routing/feedback",
                json={
                    "request_id": "req-1",
                    "signal": "copy",
                    "provider_id": "openai",
                    "task_type": "chat",
                },
            )

        bandit_update.assert_not_called()


# ── POST /routing/feedback — feedback_service path ───────────────────────────


class TestFeedbackServicePath:
    def test_thumbs_up_with_message_id_calls_feedback_service(self, client):
        mock_service = MagicMock()
        mock_service.record_explicit_rating = AsyncMock()

        with (
            _no_supabase(),
            patch(
                "api.routing.feedback_router._lookup_routing_event",
                new_callable=AsyncMock,
                return_value=(None, None, "user-123"),
            ),
            patch.dict(
                "sys.modules",
                {
                    "api.services.feedback_service": MagicMock(
                        feedback_service=mock_service,
                        FeedbackContext=MagicMock(return_value=MagicMock()),
                        FeedbackSignal=MagicMock(
                            THUMBS_UP="thumbs_up",
                            THUMBS_DOWN="thumbs_down",
                            COPY="copy",
                            DELETE="delete",
                            REGENERATE="regenerate",
                        ),
                    ),
                },
            ),
        ):
            client.post(
                "/routing/feedback",
                json={
                    "request_id": "req-1",
                    "rating": 1,
                    "signal": "thumbs_up",
                    "message_id": "msg-1",
                    "conversation_id": "conv-1",
                },
            )

        mock_service.record_explicit_rating.assert_awaited_once()

    def test_copy_signal_calls_record_copied(self, client):
        mock_service = MagicMock()
        mock_service.record_copied = AsyncMock()

        with (
            patch(
                "api.routing.feedback_router._lookup_routing_event",
                new_callable=AsyncMock,
                return_value=(None, None, "user-456"),
            ),
            patch.dict(
                "sys.modules",
                {
                    "api.services.feedback_service": MagicMock(
                        feedback_service=mock_service,
                        FeedbackContext=MagicMock(return_value=MagicMock()),
                        FeedbackSignal=MagicMock(
                            THUMBS_UP="thumbs_up",
                            THUMBS_DOWN="thumbs_down",
                            COPY="copy",
                            DELETE="delete",
                            REGENERATE="regenerate",
                        ),
                    ),
                },
            ),
        ):
            client.post(
                "/routing/feedback",
                json={
                    "request_id": "req-1",
                    "signal": "copy",
                    "message_id": "msg-1",
                    "conversation_id": "conv-1",
                },
            )

        mock_service.record_copied.assert_awaited_once()


# ── GET /feedback/stats ───────────────────────────────────────────────────────


class TestFeedbackStats:
    def test_returns_200_with_valid_shape(self, client):
        mock_stats = MagicMock(
            total_events=10,
            thumbs_up_count=7,
            thumbs_down_count=3,
            regenerate_count=1,
            delete_count=0,
            continue_count=5,
            copy_count=4,
            provider_switch_count=1,
            model_switch_count=0,
            thumbs_up_rate=0.7,
            by_department={},
            by_provider={},
            recent_events=[],
        )

        with (
            patch.dict(
                "sys.modules",
                {
                    "api.storage.database": MagicMock(
                        get_db=MagicMock(
                            return_value=AsyncMock(
                                __aenter__=AsyncMock(return_value=MagicMock()),
                                __aexit__=AsyncMock(return_value=False),
                            )
                        )
                    ),
                    "api.services.feedback_service": MagicMock(
                        feedback_service=MagicMock(
                            get_feedback_stats=AsyncMock(return_value=mock_stats)
                        )
                    ),
                },
            ),
        ):
            resp = client.get("/feedback/stats")

        assert resp.status_code == 200
        data = resp.json()
        assert "total_events" in data
        assert "thumbs_up_count" in data

    def test_db_failure_returns_zero_stats(self, client):
        with patch.dict(
            "sys.modules",
            {
                "api.storage.database": MagicMock(
                    get_db=MagicMock(side_effect=RuntimeError("db down"))
                ),
            },
        ):
            resp = client.get("/feedback/stats")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_events"] == 0

    def test_days_param_accepted(self, client):
        with patch.dict(
            "sys.modules",
            {
                "api.storage.database": MagicMock(
                    get_db=MagicMock(side_effect=RuntimeError("db down"))
                ),
            },
        ):
            resp = client.get("/feedback/stats?days=30")

        assert resp.status_code == 200


# ── Pydantic response models ──────────────────────────────────────────────────


class TestResponseModels:
    def test_feedback_response_ok_true(self):
        r = FeedbackResponse(ok=True)
        assert r.ok is True

    def test_feedback_stats_response_defaults(self):
        r = FeedbackStatsResponse()
        assert r.total_events == 0
        assert r.thumbs_up_rate == pytest.approx(0.0)
        assert r.by_department == {}
