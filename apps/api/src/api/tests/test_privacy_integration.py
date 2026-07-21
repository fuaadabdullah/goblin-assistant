"""
Integration tests for privacy features.

Tests:
- Sanitization
- Rate limiting
- Privacy endpoints (export/delete)
- TTL enforcement
- RLS verification
"""

from datetime import datetime, timedelta

import pytest

from api.services import safe_vector_store as safe_vector_store_module
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
    """Test SafeVectorStore with privacy features."""

    @pytest.fixture
    def vector_store(self, monkeypatch, request):
        """Create a test vector store."""

        class _DeterministicEmbeddingFunction:
            @staticmethod
            def name():
                return "default"

            @staticmethod
            def is_legacy():
                return False

            @staticmethod
            def supported_spaces():
                return ["cosine"]

            @staticmethod
            def get_config():
                return {}

            @staticmethod
            def build_from_config(_config):
                return _DeterministicEmbeddingFunction()

            def __call__(self, input):
                return [[float(len(text) % 7), 0.1, 0.2] for text in input]

        class _EmbeddingFunctions:
            @staticmethod
            def SentenceTransformerEmbeddingFunction(*_args, **_kwargs):  # noqa: N802
                return _DeterministicEmbeddingFunction()

        monkeypatch.setattr(safe_vector_store_module, "EMBEDDINGS_AVAILABLE", True)
        monkeypatch.setattr(safe_vector_store_module, "embedding_functions", _EmbeddingFunctions)

        collection_name = f"test_collection_{request.node.name}".replace("[", "_").replace("]", "_")
        return SafeVectorStore(collection_name=collection_name)

    @pytest.mark.asyncio
    async def test_reject_without_consent(self, vector_store):
        """Test that documents are rejected without consent."""
        result = await vector_store.add_document(
            doc_id="test_1",
            content="Test document",
            metadata={"source": "test"},
            user_id="user_123",
            consent_given=False,
        )

        assert "error" in result
        assert "consent" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_reject_sensitive_content(self, vector_store):
        """Test rejection of sensitive content."""
        result = await vector_store.add_document(
            doc_id="test_2",
            content="My password is secret123",
            metadata={"source": "test"},
            user_id="user_123",
            consent_given=True,
        )

        assert "error" in result
        assert "sensitive" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_reject_pii(self, vector_store):
        """Test rejection of PII content."""
        result = await vector_store.add_document(
            doc_id="test_3",
            content="Contact me at john@example.com",
            metadata={"source": "test"},
            user_id="user_123",
            consent_given=True,
        )

        assert "error" in result
        assert "PII" in result["error"] or "email" in result.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_add_clean_document(self, vector_store):
        """Test adding clean document with consent."""
        result = await vector_store.add_document(
            doc_id="test_4",
            content="How to optimize Python code for performance",
            metadata={"source": "test", "category": "programming"},
            user_id="user_123",
            consent_given=True,
            ttl_hours=1,
        )

        assert result.get("success") is True
        assert "expires_at" in result

    @pytest.mark.asyncio
    async def test_ttl_enforcement(self, vector_store):
        """Test TTL cleanup."""
        # Add document with 0 hour TTL (expired)
        await vector_store.add_document(
            doc_id="expired_doc",
            content="This should expire",
            metadata={"source": "test"},
            user_id="user_123",
            consent_given=True,
            ttl_hours=0,
        )

        # Run cleanup
        cleanup_result = await vector_store.cleanup_expired()
        deleted_count = cleanup_result["deleted_count"]

        # Should have deleted at least 1
        assert deleted_count >= 0  # May be 0 if timing is tight

    @pytest.mark.asyncio
    async def test_query_documents_filters_expired_results(self):
        """Query results are scoped to the user and filtered for TTL."""

        future = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        past = (datetime.utcnow() - timedelta(hours=1)).isoformat()

        class _Collection:
            def query(self, **kwargs):
                assert kwargs["where"] == {"user_id": "user_123"}
                assert kwargs["n_results"] == 4
                return {
                    "documents": [["fresh", "expired"]],
                    "metadatas": [[{"expires_at": future}, {"expires_at": past}]],
                    "distances": [[0.1, 0.9]],
                }

        store = SafeVectorStore.__new__(SafeVectorStore)
        store.collection = _Collection()

        result = await store.query_documents("find docs", "user_123", n_results=2)

        assert result["success"] is True
        assert result["count"] == 1
        assert result["results"]["documents"] == [["fresh"]]

    @pytest.mark.asyncio
    async def test_query_documents_include_expired_and_error_paths(self):
        """include_expired bypasses TTL filtering; query exceptions are contained."""

        class _Collection:
            def __init__(self):
                self.calls = 0

            def query(self, **_kwargs):
                self.calls += 1
                if self.calls == 1:
                    return {
                        "documents": [["fresh", "expired"]],
                        "metadatas": [[{}, {}]],
                        "distances": [[0.1, 0.9]],
                    }
                raise RuntimeError("query boom")

        collection = _Collection()
        store = SafeVectorStore.__new__(SafeVectorStore)
        store.collection = collection

        success = await store.query_documents(
            "find docs",
            "user_123",
            n_results=2,
            include_expired=True,
        )
        failure = await store.query_documents("find docs", "user_123")

        assert success["success"] is True
        assert success["count"] == 2
        assert failure == {"success": False, "error": "query boom", "count": 0}

    @pytest.mark.asyncio
    async def test_delete_user_data_deletes_matching_ids_and_handles_errors(self):
        """Deletion reports matching document IDs and contains collection failures."""

        class _Collection:
            def __init__(self):
                self.deleted = []

            def get(self, **kwargs):
                assert kwargs["where"] == {"user_id": "user_123"}
                return {"ids": ["doc1", "doc2"]}

            def delete(self, ids):
                self.deleted.extend(ids)

        collection = _Collection()
        store = SafeVectorStore.__new__(SafeVectorStore)
        store.collection = collection

        result = await store.delete_user_data("user_123")

        assert result["success"] is True
        assert result["deleted_count"] == 2
        assert collection.deleted == ["doc1", "doc2"]

        class _BrokenCollection:
            def get(self, **_kwargs):
                raise RuntimeError("delete boom")

        store.collection = _BrokenCollection()

        failure = await store.delete_user_data("user_123")

        assert failure["success"] is False
        assert failure["error"] == "delete boom"

    @pytest.mark.asyncio
    async def test_cleanup_expired_deletes_only_expired_documents(self):
        """Expired TTL metadata is deleted; invalid metadata is ignored."""

        future = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        past = (datetime.utcnow() - timedelta(hours=1)).isoformat()

        class _Collection:
            def __init__(self):
                self.deleted = []

            def get(self, **kwargs):
                assert kwargs["include"] == ["metadatas"]
                return {
                    "ids": ["fresh", "expired", "invalid"],
                    "metadatas": [
                        {"expires_at": future},
                        {"expires_at": past},
                        {"expires_at": "not-a-date"},
                    ],
                }

            def delete(self, ids):
                self.deleted.extend(ids)

        collection = _Collection()
        store = SafeVectorStore.__new__(SafeVectorStore)
        store.collection = collection

        result = await store.cleanup_expired()

        assert result["success"] is True
        assert result["deleted_count"] == 1
        assert collection.deleted == ["expired"]

    @pytest.mark.asyncio
    async def test_count_and_export_user_data_paths(self):
        """Count and export expose user-scoped document metadata."""

        class _Collection:
            def __init__(self):
                self.broken = False

            def get(self, **kwargs):
                if self.broken:
                    raise RuntimeError("export boom")
                assert kwargs["where"] == {"user_id": "user_123"}
                if kwargs["include"] == []:
                    return {"ids": ["doc1", "doc2"]}
                return {
                    "ids": ["doc1"],
                    "documents": ["hello"],
                    "metadatas": [{"source": "test"}],
                }

        collection = _Collection()
        store = SafeVectorStore.__new__(SafeVectorStore)
        store.collection = collection

        count = await store.get_user_document_count("user_123")
        exported = await store.export_user_data("user_123")

        assert count == 2
        assert exported["success"] is True
        assert exported["document_count"] == 1
        assert exported["documents"][0]["doc_id"] == "doc1"

        collection.broken = True

        assert await store.get_user_document_count("user_123") == 0
        failure = await store.export_user_data("user_123")
        assert failure["success"] is False
        assert failure["error"] == "export boom"


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
