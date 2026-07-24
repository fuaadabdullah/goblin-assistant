"""Estimate Tokens tests for chat_router."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from .conftest import _payload


class TestEstimateTokens:
    """Tests for POST /api/v1/chat/estimate-tokens — read-only token/cost preview."""

    @staticmethod
    def _stub_assembly_service(total_tokens: int, layers: list[dict]):
        mock_layers = []
        for layer in layers:
            ml = MagicMock()
            # MagicMock(name=...) sets the mock's repr-name, not an attribute,
            # so assign after construction.
            ml.name = layer["name"]
            ml.tokens = layer["tokens"]
            mock_layers.append(ml)
        service = MagicMock()
        service.assemble_context = AsyncMock(
            return_value={
                "context": "stub",
                "layers": mock_layers,
                "total_tokens_used": total_tokens,
            }
        )
        return service

    @staticmethod
    def _stub_provider(cost_in=1.0, cost_out=2.0):
        provider = MagicMock()
        provider.COST_INPUT_PER_1K = cost_in
        provider.COST_OUTPUT_PER_1K = cost_out
        provider.estimate_cost = lambda i, o: i * cost_in / 1000 + o * cost_out / 1000
        return provider

    def test_estimate_tokens_no_conversation(self, client):
        service = self._stub_assembly_service(
            total_tokens=1000,
            layers=[
                {"name": "system", "tokens": 300},
                {"name": "ephemeral", "tokens": 700},
            ],
        )
        provider = self._stub_provider(cost_in=1.0, cost_out=2.0)

        with (
            patch(
                "api.chat_router.messages._get_context_assembly_service",
                return_value=service,
            ),
            patch(
                "api.chat_router.messages.dispatcher.get_provider",
                return_value=provider,
            ),
            patch(
                "api.chat_router.messages.dispatcher._candidate_order",
                return_value=["openai"],
            ),
        ):
            response = client.post(
                "/api/v1/chat/estimate-tokens",
                json={"message": "hello", "provider": "openai"},
            )

        assert response.status_code == 200
        data = _payload(response)
        assert data["input_tokens"] == 1000
        assert data["estimated_output_tokens"] == 400
        # 1000 * 1.0/1000 + 400 * 2.0/1000 = 1.0 + 0.8 = 1.8
        assert data["estimated_cost_usd"] == pytest.approx(1.8)
        # Response is department-based now; provider no longer surfaced.
        assert data["department"] == "general"
        assert len(data["layers"]) == 2
        assert data["layers"][0] == {"name": "system", "tokens": 300}

    def test_estimate_tokens_with_conversation_passes_history(self, client, mock_user):
        owned = MagicMock(
            user_id=mock_user.id,
            messages=[MagicMock(role="user", content=f"msg-{i}") for i in range(15)],
        )
        service = self._stub_assembly_service(total_tokens=500, layers=[])

        async def fake_require(*_a, **_k):
            return owned

        with (
            patch(
                "api.chat_router._require_owned_conversation",
                side_effect=fake_require,
            ),
            patch(
                "api.chat_router.messages._get_context_assembly_service",
                return_value=service,
            ),
            patch(
                "api.chat_router.messages.dispatcher.get_provider",
                return_value=self._stub_provider(),
            ),
            patch(
                "api.chat_router.messages.dispatcher._candidate_order",
                return_value=["openai"],
            ),
        ):
            response = client.post(
                "/api/v1/chat/estimate-tokens?conversation_id=conv-1",
                json={"message": "hello"},
            )

        assert response.status_code == 200
        # Last-10 slice should have been passed to assemble_context
        call_kwargs = service.assemble_context.call_args.kwargs
        assert len(call_kwargs["conversation_history"]) == 10
        assert call_kwargs["conversation_history"][0]["content"] == "msg-5"
        assert call_kwargs["conversation_id"] == "conv-1"

    def test_estimate_tokens_rejects_unowned_conversation(self, client):
        async def fake_require(*_a, **_k):
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Conversation not found")

        with patch(
            "api.chat_router._require_owned_conversation",
            side_effect=fake_require,
        ):
            response = client.post(
                "/api/v1/chat/estimate-tokens?conversation_id=conv-other",
                json={"message": "hello"},
            )

        assert response.status_code == 404

    def test_estimate_tokens_never_invokes_provider(self, client):
        service = self._stub_assembly_service(
            total_tokens=100, layers=[{"name": "system", "tokens": 100}]
        )

        invoke_calls = []

        async def fake_invoke(*args, **kwargs):
            invoke_calls.append((args, kwargs))
            return {"ok": True}

        with (
            patch(
                "api.chat_router.messages._get_context_assembly_service",
                return_value=service,
            ),
            patch(
                "api.chat_router.messages.dispatcher.get_provider",
                return_value=self._stub_provider(),
            ),
            patch(
                "api.chat_router.messages.dispatcher._candidate_order",
                return_value=["openai"],
            ),
            patch(
                "api.chat_router.invoke_provider",
                side_effect=fake_invoke,
            ),
        ):
            response = client.post(
                "/api/v1/chat/estimate-tokens",
                json={"message": "hello", "provider": "openai"},
            )

        assert response.status_code == 200
        assert invoke_calls == []

    def test_estimate_tokens_handles_no_configured_providers(self, client):
        service = self._stub_assembly_service(
            total_tokens=50, layers=[{"name": "system", "tokens": 50}]
        )

        with (
            patch(
                "api.chat_router.messages._get_context_assembly_service",
                return_value=service,
            ),
            patch(
                "api.chat_router.messages.dispatcher._candidate_order",
                return_value=[],
            ),
        ):
            response = client.post(
                "/api/v1/chat/estimate-tokens",
                json={"message": "hello"},
            )

        assert response.status_code == 200
        data = _payload(response)
        # Response is department-based now; provider no longer surfaced.
        assert data["department"] == "general"
        assert data["estimated_cost_usd"] == 0.0
        assert data["degraded_mode"] is True
        assert data["degraded_reason"] == "no-configured-providers"
