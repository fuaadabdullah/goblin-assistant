"""Helpers tests for chat_router."""

from .conftest import (
    MagicMock,
)


class TestLatestSnippet:
    """Tests for _latest_snippet helper function."""

    def test_latest_snippet_empty(self):
        """Test snippet from empty conversation."""
        from api.chat_router import _latest_snippet

        mock_conv = MagicMock(messages=[])
        result = _latest_snippet(mock_conv)
        assert result is None

    def test_latest_snippet_short(self):
        """Test snippet from short message."""
        from api.chat_router import _latest_snippet

        mock_msg = MagicMock(content="Short message")
        mock_conv = MagicMock(messages=[mock_msg])
        result = _latest_snippet(mock_conv)
        assert result == "Short message"

    def test_latest_snippet_long(self):
        """Test snippet from long message."""
        from api.chat_router import _latest_snippet

        long_content = "a" * 200
        mock_msg = MagicMock(content=long_content)
        mock_conv = MagicMock(messages=[mock_msg])
        result = _latest_snippet(mock_conv)

        assert result.endswith("...")
        assert len(result) == 160


class TestExtractUsageAndCost:
    """Tests for _extract_usage_and_cost helper."""

    def test_extract_usage_and_cost_success(self):
        """Test successful extraction."""
        from api.chat_router import _extract_usage_and_cost

        provider_response = {
            "result": {
                "raw": {
                    "usage": {"tokens": 100},
                    "cost_usd": 0.05,
                    "correlation_id": "corr_123",
                }
            }
        }

        usage, cost, corr_id = _extract_usage_and_cost(provider_response)

        assert usage == {"tokens": 100}
        assert cost == 0.05
        assert corr_id == "corr_123"

    def test_extract_usage_and_cost_none(self):
        """Test extraction with no data."""
        from api.chat_router import _extract_usage_and_cost

        usage, cost, corr_id = _extract_usage_and_cost(None)

        assert usage is None
        assert cost is None
        assert corr_id is None

    def test_extract_usage_and_cost_missing_fields(self):
        """Test extraction with missing fields."""
        from api.chat_router import _extract_usage_and_cost

        provider_response = {"result": {"raw": {}}}

        usage, cost, corr_id = _extract_usage_and_cost(provider_response)

        assert usage is None
        assert cost is None
        assert corr_id is None
