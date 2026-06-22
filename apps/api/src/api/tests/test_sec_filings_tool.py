"""Tests for SEC filing tools."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from api.assistant_tools import sec_filings  # noqa: F401 - registration side effect
from api.assistant_tools.registry import TOOL_REGISTRY
from api.services import sec_filings_service as service


class TestSecFilingToolRegistration:
    EXPECTED = {
        "search_filings",
        "get_filing",
        "get_filing_section",
        "summarize_filing_section",
    }

    def test_tools_registered(self):
        assert self.EXPECTED.issubset(TOOL_REGISTRY.keys())

    def test_tools_category(self):
        for name in self.EXPECTED:
            assert TOOL_REGISTRY[name].category == "finance"


class TestSecFilingService:
    @pytest.fixture
    def sample_company(self):
        return [
            {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
        ]

    @pytest.fixture
    def sample_recent_filings(self):
        return {
            "filings": {
                "recent": {
                    "form": ["10-K", "8-K"],
                    "accessionNumber": ["0000320193-24-000123", "0000320193-24-000124"],
                    "primaryDocument": ["aapl-20240928.htm", "aapl-8k.htm"],
                    "primaryDocDescription": ["10-K", "8-K"],
                    "filingDate": ["2024-11-01", "2024-11-02"],
                    "reportDate": ["2024-09-28", "2024-11-01"],
                    "acceptanceDateTime": ["2024-11-01T18:00:00.000Z", "2024-11-02T18:00:00.000Z"],
                    "act": ["34", "34"],
                    "fileNumber": ["001-36743", "001-36743"],
                    "filmNumber": ["241234567", "241234568"],
                }
            }
        }

    def test_search_filings_returns_structured_result(self, sample_company, sample_recent_filings):
        with (
            patch.object(service, "_company_index", return_value=sample_company),
            patch.object(service, "_get_json", return_value=sample_recent_filings),
        ):
            payload = service.search_filings("AAPL", filing_types=["10-K"], limit=3)

        assert payload["company"]["ticker"] == "AAPL"
        assert payload["results"][0]["form"] == "10-K"
        assert payload["results"][0]["document_url"].endswith("aapl-20240928.htm")

    def test_get_filing_section_extracts_section(self, sample_company, sample_recent_filings):
        sample_html = """
            <html><body>
            <h1>Item 1. Business</h1>
            <p>Apple designs products. Apple sells services.</p>
            <h1>Item 1A. Risk Factors</h1>
            <p>Risks include supply chain issues and competition.</p>
            </body></html>
        """
        with (
            patch.object(service, "_company_index", return_value=sample_company),
            patch.object(service, "_get_json", return_value=sample_recent_filings),
            patch.object(service, "_fetch_text", return_value=service._html_to_text(sample_html)),
        ):
            payload = service.get_filing_section("AAPL", section="risk factors", filing_type="10-K")

        assert payload["section"] == "risk factors"
        assert "supply chain issues" in payload["section_text"].lower()

    def test_summarize_filing_section_produces_summary(self, sample_company, sample_recent_filings):
        sample_html = """
            <html><body>
            <h1>Item 1A. Risk Factors</h1>
            <p>Risks include supply chain issues. Competition may reduce margins.</p>
            <p>Demand can change quickly.</p>
            </body></html>
        """
        with (
            patch.object(service, "_company_index", return_value=sample_company),
            patch.object(service, "_get_json", return_value=sample_recent_filings),
            patch.object(service, "_fetch_text", return_value=service._html_to_text(sample_html)),
        ):
            payload = service.summarize_filing_section(
                "AAPL", section="risk factors", filing_type="10-K"
            )

        assert payload["summary"]
        assert payload["key_points"]

    @pytest.mark.asyncio
    async def test_handler_round_trip(self, sample_company, sample_recent_filings):
        with (
            patch.object(service, "_company_index", return_value=sample_company),
            patch.object(service, "_get_json", return_value=sample_recent_filings),
        ):
            payload = await TOOL_REGISTRY["search_filings"].handler(
                query="AAPL", filing_type="10-K"
            )

        assert payload["results"]
