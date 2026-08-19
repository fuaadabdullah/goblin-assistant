"""
Integration tests for privacy features.

Tests:
- Sanitization
- Rate limiting
- Privacy endpoints (export/delete)
- TTL enforcement
- RLS verification
"""

import pytest

from api.services.safe_vector_store import SafeVectorStore

# Import modules
from api.services.sanitization import (
    hash_message_id,
    is_sensitive_content,
    mask_sensitive,
    sanitize_input_for_model,
)
from api.services.telemetry import log_conversation_event, log_inference_metrics


class TestSanitization:
    """Test input sanitization and PII detection."""

    def test_email_detection(self):
        """Test email PII detection."""
        text = "Contact me at john@example.com for details"
        sanitized, pii = sanitize_input_for_model(text)

        assert "REDACTED" in sanitized
        assert "email" in pii
        assert "john@example.com" not in sanitized

    def test_phone_detection(self):
        """Test phone number detection."""
        text = "Call me at 555-123-4567"
        sanitized, pii = sanitize_input_for_model(text)

        assert "REDACTED" in sanitized
        assert "phone" in pii

    def test_api_key_detection(self):
        """Test API key detection."""
        text = "My api_key is sk-1234567890abcdef1234567890"
        sanitized, pii = sanitize_input_for_model(text)

        assert "REDACTED" in sanitized
        assert "sk_key" in pii  # OpenAI-style keys detected as sk_key

    def test_ssn_detection(self):
        """Test SSN detection."""
        text = "My SSN is 123-45-6789"
        sanitized, pii = sanitize_input_for_model(text)

        assert "REDACTED" in sanitized
        assert "ssn" in pii

    def test_clean_text(self):
        """Test clean text passes through."""
        text = "How do I optimize my Python code?"
        sanitized, pii = sanitize_input_for_model(text)

        assert sanitized == text
        assert len(pii) == 0

    def test_sensitive_content_detection(self):
        """Test sensitive keyword detection."""
        assert is_sensitive_content("My password is 12345") is True
        assert is_sensitive_content("The secret key is abc") is True
        assert is_sensitive_content("How do I use FastAPI?") is False

    def test_mask_sensitive_dict(self):
        """Test dictionary masking."""
        data = {
            "username": "john",
            "password": "secret123",
            "api_key": "sk-1234",
            "message": "Hello world",
        }

        masked = mask_sensitive(data)

        assert masked["password"] == "[REDACTED]"
        assert masked["api_key"] == "[REDACTED]"
        assert masked["username"] == "john"  # Not sensitive
        assert masked["message"] == "Hello world"

    def test_hash_message_id(self):
        """Test message ID hashing."""
        msg1 = "Hello world"
        msg2 = "Hello world"
        msg3 = "Different message"

        hash1 = hash_message_id(msg1)
        hash2 = hash_message_id(msg2)
        hash3 = hash_message_id(msg3)

        assert hash1 == hash2  # Same message = same hash
        assert hash1 != hash3  # Different message = different hash
        assert len(hash1) == 16  # Truncated to 16 chars


class TestVectorStore:
    """Test SafeVectorStore privacy enforcement (consent, PII, TTL) and delegation."""

    class _MockStore:
        """Minimal VectorStore stub — records upsert calls."""

        def __init__(self):
            self.upserted: list = []

        async def upsert(self, doc_id, content, embedding, user_id, metadata=None):
            self.upserted.append({"doc_id": doc_id, "content": content, "metadata": metadata or {}})

        async def query(self, embedding, user_id, n_results=10):
            return []

        async def delete_user_data(self, user_id):
            return {"success": True, "deleted_count": 2, "user_id": user_id}

        async def export_user_data(self, user_id):
            return {
                "success": True,
                "document_count": 1,
                "documents": [{"id": "doc1", "content": "hello", "metadata": {"source": "test"}}],
            }

        async def get_user_document_count(self, user_id):
            return 2

        async def health(self):
            return {"status": "healthy", "backend": "mock"}

    @pytest.fixture
    def mock_store(self):
        return self._MockStore()

    @pytest.fixture
    def vector_store(self, mock_store):
        return SafeVectorStore(store=mock_store)

    @pytest.mark.asyncio
    async def test_reject_without_consent(self, vector_store):
        """Documents are rejected when consent is not given."""
        result = await vector_store.add_document(
            doc_id="test_1",
            content="Test document",
            embedding=[0.1, 0.2, 0.3],
            metadata={"source": "test"},
            user_id="user_123",
            consent_given=False,
        )
        assert "error" in result
        assert "consent" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_reject_sensitive_content(self, vector_store):
        """Documents containing sensitive keywords are rejected before upsert."""
        result = await vector_store.add_document(
            doc_id="test_2",
            content="My password is secret123",
            embedding=[0.1, 0.2, 0.3],
            metadata={"source": "test"},
            user_id="user_123",
            consent_given=True,
        )
        assert "error" in result
        assert "sensitive" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_reject_pii(self, vector_store):
        """Documents with detectable PII are rejected before upsert."""
        result = await vector_store.add_document(
            doc_id="test_3",
            content="Contact me at john@example.com",
            embedding=[0.1, 0.2, 0.3],
            metadata={"source": "test"},
            user_id="user_123",
            consent_given=True,
        )
        assert "error" in result
        assert "PII" in result["error"] or "email" in result.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_add_clean_document(self, vector_store, mock_store):
        """Clean documents with consent are upserted and return success with expires_at."""
        result = await vector_store.add_document(
            doc_id="test_4",
            content="How to optimize Python code for performance",
            embedding=[0.1, 0.2, 0.3],
            metadata={"source": "test", "category": "programming"},
            user_id="user_123",
            consent_given=True,
            ttl_hours=1,
        )
        assert result.get("success") is True
        assert "expires_at" in result
        assert len(mock_store.upserted) == 1

    @pytest.mark.asyncio
    async def test_ttl_metadata_attached(self, vector_store, mock_store):
        """TTL metadata (expires_at, created_at, consent_given) is written to the store."""
        await vector_store.add_document(
            doc_id="ttl_doc",
            content="How to write clean code",
            embedding=[0.1, 0.2, 0.3],
            metadata={"source": "test"},
            user_id="user_123",
            consent_given=True,
            ttl_hours=2,
        )
        assert len(mock_store.upserted) == 1
        meta = mock_store.upserted[0]["metadata"]
        assert "expires_at" in meta
        assert "created_at" in meta
        assert meta["consent_given"] is True

    @pytest.mark.asyncio
    async def test_delete_user_data_delegates_to_store(self, vector_store):
        """delete_user_data delegates to the underlying VectorStore."""
        result = await vector_store.delete_user_data("user_123")
        assert result["success"] is True
        assert result["deleted_count"] == 2

    @pytest.mark.asyncio
    async def test_export_user_data_delegates_to_store(self, vector_store):
        """export_user_data delegates to the underlying VectorStore."""
        result = await vector_store.export_user_data("user_123")
        assert result["success"] is True
        assert result["document_count"] == 1

    @pytest.mark.asyncio
    async def test_get_user_document_count_delegates_to_store(self, vector_store):
        """get_user_document_count delegates to the underlying VectorStore."""
        count = await vector_store.get_user_document_count("user_123")
        assert count == 2

    @pytest.mark.asyncio
    async def test_health_delegates_to_store(self, vector_store):
        """health() delegates to the underlying VectorStore."""
        result = await vector_store.health()
        assert result["status"] == "healthy"
        assert result["backend"] == "mock"


class TestTelemetry:
    """Test telemetry with redaction."""

    def test_log_inference_metrics(self):
        """Test inference logging without message content."""
        # This should not raise any exceptions
        log_inference_metrics(
            provider="openai",
            model="gpt-4",
            latency_ms=150,
            token_count=50,
            cost_usd=0.002,
            status_code=200,
            user_id="user_123",
        )

        # No assertions - just verify it doesn't crash
        # In production, verify Datadog receives metrics

    def test_log_conversation_event(self):
        """Test conversation event logging with hash."""
        event = log_conversation_event(
            event_type="message_sent", user_id="user_123", metadata={"source": "web"}
        )

        assert event["event"] == "message_sent"
        assert "user_id_hash" in event
        assert event["user_id_hash"] != "user_123"  # Should be hashed
        assert "timestamp" in event


class TestRateLimiting:
    """Test rate limiting middleware."""

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self):
        """Test rate limit enforcement."""
        # This would require a running Redis instance
        # and FastAPI test client
        # For now, mark as integration test
        pytest.skip("Requires running Redis and FastAPI server")

    @pytest.mark.asyncio
    async def test_rate_limit_headers(self):
        """Test rate limit headers in response."""
        pytest.skip("Requires running FastAPI server")


class TestPrivacyEndpoints:
    """Test GDPR/CCPA endpoints."""

    @pytest.mark.asyncio
    async def test_export_user_data(self):
        """Test data export endpoint."""
        pytest.skip("Requires running FastAPI server with auth")

    @pytest.mark.asyncio
    async def test_delete_user_data(self):
        """Test data deletion endpoint."""
        pytest.skip("Requires running FastAPI server with auth")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
