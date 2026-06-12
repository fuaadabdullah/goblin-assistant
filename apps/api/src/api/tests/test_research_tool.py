"""Tests for lightweight research assistant tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from api.assistant_tools import research_tool  # noqa: F401 - registration side effect
from api.assistant_tools.registry import TOOL_REGISTRY


class TestResearchToolRegistration:
    def test_registered(self):
        assert "lightweight_research" in TOOL_REGISTRY
        assert "verify_sources" in TOOL_REGISTRY
        assert "research_pdf_extract" in TOOL_REGISTRY
        assert TOOL_REGISTRY["lightweight_research"].category == "research"


class TestLightweightResearch:
    @pytest.mark.asyncio
    async def test_web_only(self):
        mock_web = AsyncMock(
            return_value={
                "results": [
                    {"title": "A", "url": "https://a.example.com", "snippet": "alpha"},
                ]
            }
        )
        with patch("api.assistant_tools.skills.research_tool._handle_web_search", mock_web):
            result = await TOOL_REGISTRY["lightweight_research"].handler(
                query="topic",
                include_web=True,
                include_academic=False,
                max_sources=5,
            )
        assert "error" not in result
        assert result["coverage"]["providers"]["web_search"]["ok"] is True
        assert len(result["sources"]) == 1
        assert result["sources"][0]["source_type"] == "web"

    @pytest.mark.asyncio
    async def test_combined_web_and_academic(self):
        mock_web = AsyncMock(
            return_value={
                "results": [
                    {"title": "Web 1", "url": "https://w1.example.com", "snippet": "w"},
                ]
            }
        )
        mock_acad = AsyncMock(
            return_value={
                "results": [
                    {
                        "title": "Paper 1",
                        "url": "https://arxiv.org/abs/1234.5678",
                        "abstract": "paper summary",
                    }
                ]
            }
        )
        with (
            patch("api.assistant_tools.skills.research_tool._handle_web_search", mock_web),
            patch("api.assistant_tools.skills.research_tool._handle_academic_search", mock_acad),
        ):
            result = await TOOL_REGISTRY["lightweight_research"].handler(
                query="topic", max_sources=6
            )

        assert "error" not in result
        assert len(result["sources"]) == 2
        assert result["coverage"]["providers"]["web_search"]["count"] == 1
        assert result["coverage"]["providers"]["academic_search"]["count"] == 1
        assert isinstance(result["brief"], str)
        assert result["findings"]

    @pytest.mark.asyncio
    async def test_partial_failure_keeps_successful_provider(self):
        mock_web = AsyncMock(return_value={"error": "web down"})
        mock_acad = AsyncMock(
            return_value={
                "results": [
                    {"title": "Paper", "url": "https://arxiv.org/abs/1", "abstract": "ok"},
                ]
            }
        )
        with (
            patch("api.assistant_tools.skills.research_tool._handle_web_search", mock_web),
            patch("api.assistant_tools.skills.research_tool._handle_academic_search", mock_acad),
        ):
            result = await TOOL_REGISTRY["lightweight_research"].handler(query="topic")

        assert "error" not in result
        assert result["coverage"]["partial_failures"]
        assert result["coverage"]["providers"]["web_search"]["ok"] is False
        assert result["coverage"]["providers"]["academic_search"]["ok"] is True
        assert len(result["sources"]) == 1

    @pytest.mark.asyncio
    async def test_all_providers_disabled_rejected(self):
        result = await TOOL_REGISTRY["lightweight_research"].handler(
            query="topic",
            include_web=False,
            include_academic=False,
        )
        assert "error" in result


class TestVerifySources:
    @pytest.mark.asyncio
    async def test_valid_source_passes_with_high_confidence(self):
        result = await TOOL_REGISTRY["verify_sources"].handler(
            sources=[
                {
                    "title": "Attention Is All You Need",
                    "url": "https://arxiv.org/abs/1706.03762",
                    "source_type": "academic",
                    "published_at": "2017-06-12",
                }
            ]
        )
        assert "error" not in result
        assert result["summary"]["verified_sources"] == 1
        assert result["verified_sources"][0]["verification"]["confidence"] >= 0.7

    @pytest.mark.asyncio
    async def test_malformed_and_duplicate_sources_are_flagged(self):
        result = await TOOL_REGISTRY["verify_sources"].handler(
            sources=[
                {"title": "One", "url": "notaurl", "source_type": "web"},
                {"title": "One", "url": "https://x.example.com/a", "source_type": "web"},
                {"title": "One", "url": "https://x.example.com/a/", "source_type": "web"},
            ]
        )
        assert "error" not in result
        first_issues = result["verified_sources"][0]["verification"]["issues"]
        assert "malformed_url" in first_issues
        third_warnings = result["verified_sources"][2]["verification"]["warnings"]
        assert any("duplicate_url_with_index_" in warning for warning in third_warnings)

    @pytest.mark.asyncio
    async def test_missing_metadata_and_confidence_aggregation(self):
        result = await TOOL_REGISTRY["verify_sources"].handler(
            sources=[
                {"url": "https://example.com", "source_type": "web"},
                {"title": "Missing URL", "source_type": "web"},
            ],
            strictness="standard",
        )
        assert "error" not in result
        assert result["summary"]["total_sources"] == 2
        assert result["summary"]["average_confidence"] < 1.0
        assert result["summary"]["flagged_sources"] >= 1


class TestResearchPdfExtract:
    @pytest.mark.asyncio
    async def test_text_pdf_success(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        pdf_path = tmp_path / "papers" / "a.pdf"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_bytes(b"%PDF-1.4 test")

        fake_extract = {
            "pdf_extraction_status": "success",
            "page_count": 2,
            "char_count": 100,
            "chunks": [{"chunk_id": "p1-c1", "text": "alpha"}],
            "warnings": [],
            "ocr_attempted": False,
        }
        with patch(
            "api.assistant_tools.skills.research_tool.extract_pdf", return_value=fake_extract
        ):
            result = await TOOL_REGISTRY["research_pdf_extract"].handler(path="papers/a.pdf")

        assert "error" not in result
        assert result["pdf_extraction_status"] == "success"
        assert result["selected_count"] == 1

    @pytest.mark.asyncio
    async def test_no_text_or_ocr_deps_reported(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        pdf_path = tmp_path / "papers" / "b.pdf"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_bytes(b"%PDF-1.4 test")

        fake_extract = {
            "pdf_extraction_status": "ocr_missing_deps",
            "page_count": 1,
            "char_count": 0,
            "chunks": [],
            "warnings": ["ocr_deps_unavailable: tesseract missing"],
            "ocr_attempted": True,
        }
        with patch(
            "api.assistant_tools.skills.research_tool.extract_pdf", return_value=fake_extract
        ):
            result = await TOOL_REGISTRY["research_pdf_extract"].handler(path="papers/b.pdf")

        assert result["pdf_extraction_status"] == "ocr_missing_deps"
        assert result["selected_count"] == 0
        assert result["ocr_attempted"] is True

    @pytest.mark.asyncio
    async def test_chunk_bounds_respected_without_query(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        pdf_path = tmp_path / "papers" / "c.pdf"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_bytes(b"%PDF-1.4 test")

        chunks = [{"chunk_id": f"c{i}", "text": f"text-{i}"} for i in range(20)]
        fake_extract = {
            "pdf_extraction_status": "success",
            "page_count": 5,
            "char_count": 1000,
            "chunks": chunks,
            "warnings": [],
            "ocr_attempted": False,
        }
        with patch(
            "api.assistant_tools.skills.research_tool.extract_pdf", return_value=fake_extract
        ):
            result = await TOOL_REGISTRY["research_pdf_extract"].handler(
                path="papers/c.pdf", max_chunks=3
            )

        assert result["selected_count"] == 3
        assert result["total_chunks"] == 20

    @pytest.mark.asyncio
    async def test_query_uses_relevance_selection(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        pdf_path = tmp_path / "papers" / "d.pdf"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_bytes(b"%PDF-1.4 test")

        chunks = [{"chunk_id": "base", "text": "base text"}]
        fake_extract = {
            "pdf_extraction_status": "success",
            "page_count": 1,
            "char_count": 100,
            "chunks": chunks,
            "warnings": [],
            "ocr_attempted": False,
        }
        selected = [{"chunk_id": "rel-1", "text": "relevant"}]
        with (
            patch(
                "api.assistant_tools.skills.research_tool.extract_pdf", return_value=fake_extract
            ),
            patch(
                "api.assistant_tools.skills.research_tool.select_relevant_chunks",
                return_value=selected,
            ) as mock_select,
        ):
            result = await TOOL_REGISTRY["research_pdf_extract"].handler(
                path="papers/d.pdf",
                query="what is relevant",
                max_chunks=4,
            )

        mock_select.assert_called_once()
        assert result["selected_chunks"] == selected
