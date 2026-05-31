"""Tests for PDF extraction and chunk relevance helpers."""

from __future__ import annotations

from api.services import pdf_extraction_service as svc


class TestPdfExtraction:
    def test_text_pdf_extracts_chunks(self, monkeypatch):
        monkeypatch.setattr(
            svc,
            "_extract_with_pypdf",
            lambda _path: (["First page text", "Second page text"], []),
        )

        result = svc.extract_pdf("/tmp/example.pdf")

        assert result["pdf_extraction_status"] == "success"
        assert result["page_count"] == 2
        assert result["char_count"] > 0
        assert len(result["chunks"]) >= 2
        assert result["chunks"][0]["page_start"] == 1

    def test_no_text_without_ocr_is_non_fatal(self, monkeypatch):
        monkeypatch.setattr(
            svc,
            "_extract_with_pypdf",
            lambda _path: (["", ""], []),
        )
        monkeypatch.delenv("GOBLIN_PDF_OCR_ENABLED", raising=False)

        result = svc.extract_pdf("/tmp/empty.pdf")

        assert result["pdf_extraction_status"] == "no_text"
        assert result["char_count"] == 0
        assert "no_extractable_text" in result["warnings"]

    def test_ocr_enabled_missing_deps_is_graceful(self, monkeypatch):
        monkeypatch.setattr(
            svc,
            "_extract_with_pypdf",
            lambda _path: ([""], []),
        )
        monkeypatch.setattr(
            svc,
            "_extract_with_ocr",
            lambda _path: ([], ["ocr_deps_unavailable: missing"]),
        )
        monkeypatch.setenv("GOBLIN_PDF_OCR_ENABLED", "true")

        result = svc.extract_pdf("/tmp/scanned.pdf")

        assert result["pdf_extraction_status"] == "ocr_missing_deps"
        assert result["ocr_attempted"] is True
        assert any("ocr_deps_unavailable" in warning for warning in result["warnings"])


class TestChunkSelection:
    def test_relevance_selection_and_char_cap(self):
        chunks = [
            {"chunk_id": "a", "page_start": 1, "page_end": 1, "text": "apple banana orange market"},
            {"chunk_id": "b", "page_start": 2, "page_end": 2, "text": "completely unrelated topic"},
            {
                "chunk_id": "c",
                "page_start": 3,
                "page_end": 3,
                "text": "apple apple earnings and market data",
            },
        ]

        selected = svc.select_relevant_chunks(
            query="apple market earnings",
            chunks=chunks,
            max_chunks=2,
            max_chars=40,
        )

        assert len(selected) >= 1
        total_chars = sum(len(c["text"]) for c in selected)
        assert total_chars <= 41  # allow 1 char for truncation marker replacement behavior
        assert selected[0]["chunk_id"] in {"a", "c"}
