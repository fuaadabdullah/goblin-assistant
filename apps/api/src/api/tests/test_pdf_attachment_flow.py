"""Unit tests for PDF extraction wiring in upload/message routes."""

from __future__ import annotations

import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.datastructures import UploadFile

from api.auth.router import User
from api.chat_router import uploads as uploads_module
from api.chat_router.messages import send_message
from api.chat_router.schemas import SendMessageRequest
from api.chat_router.uploads import _pending_uploads, upload_file


class TestPdfUploadExtraction:
    @pytest.mark.asyncio
    async def test_upload_pdf_stores_extraction_metadata(self, monkeypatch):
        monkeypatch.setattr(
            "api.chat_router.uploads.extract_pdf",
            lambda _path: {
                "pdf_extraction_status": "success",
                "page_count": 2,
                "char_count": 123,
                "chunks": [{"chunk_id": "p1-c1", "page_start": 1, "page_end": 1, "text": "alpha"}],
                "warnings": [],
                "ocr_attempted": False,
            },
        )
        _pending_uploads.clear()
        uploads_module._pdf_extraction_cache_by_hash.clear()
        uploads_module._pdf_embedding_cache_by_user_hash.clear()

        file = UploadFile(
            filename="doc.pdf",
            file=io.BytesIO(b"%PDF-1.4\nmock\n%%EOF"),
            headers={"content-type": "application/pdf"},
        )
        current_user = User(id="test-user", email="test@example.com")

        response = await upload_file(file=file, current_user=current_user)

        file_id = response.file_id
        assert file_id in _pending_uploads
        meta = _pending_uploads[file_id]
        assert meta["pdf_extraction_status"] == "success"
        assert meta["page_count"] == 2
        assert len(meta["chunks"]) == 1

    @pytest.mark.asyncio
    async def test_non_pdf_upload_preserves_existing_behavior(self):
        _pending_uploads.clear()
        uploads_module._pdf_extraction_cache_by_hash.clear()
        uploads_module._pdf_embedding_cache_by_user_hash.clear()
        file = UploadFile(
            filename="notes.txt",
            file=io.BytesIO(b"hello"),
            headers={"content-type": "text/plain"},
        )
        current_user = User(id="test-user", email="test@example.com")

        response = await upload_file(file=file, current_user=current_user)

        meta = _pending_uploads[response.file_id]
        assert "pdf_extraction_status" not in meta
        assert meta["mime_type"] == "text/plain"

    @pytest.mark.asyncio
    async def test_upload_pdf_uses_hash_cache_for_extraction(self, monkeypatch):
        _pending_uploads.clear()
        uploads_module._pdf_extraction_cache_by_hash.clear()
        uploads_module._pdf_embedding_cache_by_user_hash.clear()

        extract_calls = {"count": 0}

        def _fake_extract(_path):
            extract_calls["count"] += 1
            return {
                "pdf_extraction_status": "success",
                "page_count": 1,
                "char_count": 10,
                "chunks": [{"chunk_id": "p1-c1", "page_start": 1, "page_end": 1, "text": "alpha"}],
                "warnings": [],
                "ocr_attempted": False,
            }

        monkeypatch.setattr("api.chat_router.uploads.extract_pdf", _fake_extract)

        current_user = User(id="test-user", email="test@example.com")
        file_bytes = b"%PDF-1.4\nmock-cache\n%%EOF"

        file_one = UploadFile(
            filename="doc-one.pdf",
            file=io.BytesIO(file_bytes),
            headers={"content-type": "application/pdf"},
        )
        file_two = UploadFile(
            filename="doc-two.pdf",
            file=io.BytesIO(file_bytes),
            headers={"content-type": "application/pdf"},
        )

        first = await upload_file(file=file_one, current_user=current_user)
        second = await upload_file(file=file_two, current_user=current_user)

        first_meta = _pending_uploads[first.file_id]
        second_meta = _pending_uploads[second.file_id]

        assert extract_calls["count"] == 1
        assert first_meta["pdf_extraction_cache_hit"] is False
        assert second_meta["pdf_extraction_cache_hit"] is True
        assert second_meta["pdf_embedding_cache_hit"] is True


class TestPdfContextInjection:
    @pytest.mark.asyncio
    async def test_send_message_injects_pdf_context(self):
        _pending_uploads.clear()
        conversation_id = "conv-1"
        current_user = User(id="test-user", email="test@example.com")

        _pending_uploads["pdf-att-1"] = {
            "file_id": "pdf-att-1",
            "user_id": current_user.id,
            "filename": "report.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 1024,
            "storage_key": "x",
            "upload_hash": "h",
            "path": "/tmp/report.pdf",
            "pdf_extraction_status": "success",
            "page_count": 1,
            "char_count": 200,
            "chunks": [
                {
                    "chunk_id": "p1-c1",
                    "page_start": 1,
                    "page_end": 1,
                    "text": "Revenue increased to 45 million in Q4 and margins improved.",
                }
            ],
            "warnings": [],
        }

        owned_conversation = SimpleNamespace(
            conversation_id=conversation_id,
            user_id=current_user.id,
            messages=[SimpleNamespace(role="user", content="hi")],
        )
        captured_payload: dict = {}

        async def fake_require_owned_conversation(*_args, **_kwargs):
            return owned_conversation

        async def fake_invoke_provider(pid, model, payload, timeout_ms, stream=False):
            _ = (pid, model, timeout_ms, stream)
            captured_payload["messages"] = payload["messages"]
            return {
                "ok": True,
                "provider": "openai",
                "model": "gpt-4o-mini",
                "result": {"text": "ok", "raw": {}},
            }

        mock_wti = MagicMock()
        mock_wti.process_message = AsyncMock(
            return_value={
                "classification": {"type": "working", "confidence": 1.0},
                "decision": {"actions": [], "confidence": 1.0},
                "execution": {"actions_executed": []},
                "processed_at": "2026-05-30T00:00:00.000000",
            }
        )

        mock_classifier = MagicMock()
        mock_classifier.classify_message.return_value = SimpleNamespace(message_type="generic")
        fake_message_type = SimpleNamespace(LEARNING="learning")

        with (
            patch(
                "api.chat_router.messages._cr._require_owned_conversation",
                side_effect=fake_require_owned_conversation,
            ),
            patch(
                "api.chat_router.messages._cr.conversation_store.add_message_to_conversation",
                new=AsyncMock(return_value=True),
            ),
            patch("api.chat_router.messages._cr.invoke_provider", side_effect=fake_invoke_provider),
            patch("api.chat_router.messages._get_write_time_intelligence", return_value=mock_wti),
            patch(
                "api.chat_router.messages._get_message_classifier",
                return_value=(mock_classifier, fake_message_type),
            ),
            patch("api.chat_router.messages.schedule_conversation_archive", new_callable=AsyncMock),
            patch("api.chat_router.messages.event_emitter.emit", new_callable=AsyncMock),
        ):
            response = await send_message(
                conversation_id=conversation_id,
                request=SendMessageRequest(
                    message="What does the PDF say about revenue and margins?",
                    provider="openai",
                    model="gpt-4o-mini",
                    enable_context_assembly=False,
                    attachment_ids=["pdf-att-1"],
                ),
                current_user=current_user,
            )

        assert response.success is True
        messages = captured_payload["messages"]
        assert messages[0]["role"] == "system"
        assert "Attachment context extracted from user-provided PDFs" in messages[0]["content"]
        assert "Revenue increased to 45 million" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_context_char_cap_is_enforced(self, monkeypatch):
        monkeypatch.setenv("GOBLIN_ATTACHMENT_CONTEXT_MAX_CHARS", "120")
        _pending_uploads.clear()

        conversation_id = "conv-2"
        current_user = User(id="test-user", email="test@example.com")
        _pending_uploads["pdf-att-2"] = {
            "file_id": "pdf-att-2",
            "user_id": current_user.id,
            "filename": "long.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 2048,
            "storage_key": "x",
            "upload_hash": "h",
            "path": "/tmp/long.pdf",
            "chunks": [
                {
                    "chunk_id": "p1-c1",
                    "page_start": 1,
                    "page_end": 1,
                    "text": "apple " * 300,
                }
            ],
        }

        owned_conversation = SimpleNamespace(
            conversation_id=conversation_id,
            user_id=current_user.id,
            messages=[SimpleNamespace(role="user", content="hello")],
        )
        captured_payload: dict = {}

        async def fake_require_owned_conversation(*_args, **_kwargs):
            return owned_conversation

        async def fake_invoke_provider(pid, model, payload, timeout_ms, stream=False):
            _ = (pid, model, timeout_ms, stream)
            captured_payload["messages"] = payload["messages"]
            return {
                "ok": True,
                "provider": "openai",
                "model": "gpt-4o-mini",
                "result": {"text": "ok", "raw": {}},
            }

        mock_wti = MagicMock()
        mock_wti.process_message = AsyncMock(
            return_value={
                "classification": {"type": "working", "confidence": 1.0},
                "decision": {"actions": [], "confidence": 1.0},
                "execution": {"actions_executed": []},
                "processed_at": "2026-05-30T00:00:00.000000",
            }
        )

        mock_classifier = MagicMock()
        mock_classifier.classify_message.return_value = SimpleNamespace(message_type="generic")
        fake_message_type = SimpleNamespace(LEARNING="learning")

        with (
            patch(
                "api.chat_router.messages._cr._require_owned_conversation",
                side_effect=fake_require_owned_conversation,
            ),
            patch(
                "api.chat_router.messages._cr.conversation_store.add_message_to_conversation",
                new=AsyncMock(return_value=True),
            ),
            patch("api.chat_router.messages._cr.invoke_provider", side_effect=fake_invoke_provider),
            patch("api.chat_router.messages._get_write_time_intelligence", return_value=mock_wti),
            patch(
                "api.chat_router.messages._get_message_classifier",
                return_value=(mock_classifier, fake_message_type),
            ),
            patch("api.chat_router.messages.schedule_conversation_archive", new_callable=AsyncMock),
            patch("api.chat_router.messages.event_emitter.emit", new_callable=AsyncMock),
        ):
            response = await send_message(
                conversation_id=conversation_id,
                request=SendMessageRequest(
                    message="summarize apple mentions",
                    provider="openai",
                    model="gpt-4o-mini",
                    enable_context_assembly=False,
                    attachment_ids=["pdf-att-2"],
                ),
                current_user=current_user,
            )

        assert response.success is True
        context_msg = captured_payload["messages"][0]["content"]
        assert len(context_msg) < 1000
