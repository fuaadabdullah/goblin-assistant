"""SEC filing retrieval and section extraction helpers."""

from __future__ import annotations

import html
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence

import httpx

SEC_BASE_URL = "https://www.sec.gov"
SEC_DATA_URL = "https://data.sec.gov"
DEFAULT_FILING_TYPES = {"10-K", "10-Q", "8-K", "4"}


def _user_agent() -> str:
    return os.getenv(
        "SEC_USER_AGENT",
        "GoblinAssistant/1.0 (contact: support@goblin.local)",
    )


def _headers() -> Dict[str, str]:
    return {
        "User-Agent": _user_agent(),
        "Accept-Encoding": "gzip, deflate",
        "Host": "www.sec.gov",
    }


@dataclass(frozen=True)
class CompanyIdentity:
    cik: str
    ticker: Optional[str]
    title: str


def _normalize_cik(value: Any) -> Optional[str]:
    if value is None:
        return None
    digits = re.sub(r"\D", "", str(value))
    if not digits:
        return None
    return digits.lstrip("0") or "0"


def _cik_path(cik: str) -> str:
    return f"{int(cik):010d}"


def _archive_path(cik: str, accession_number: str, primary_document: str) -> str:
    accession_dir = accession_number.replace("-", "")
    return f"{SEC_BASE_URL}/Archives/edgar/data/{int(cik)}/{accession_dir}/{primary_document}"


def _submission_url(cik: str) -> str:
    return f"{SEC_DATA_URL}/submissions/CIK{_cik_path(cik)}.json"


@lru_cache(maxsize=1)
def _company_index() -> List[Dict[str, Any]]:
    url = f"{SEC_DATA_URL}/files/company_tickers.json"
    with httpx.Client(timeout=20.0, headers=_headers(), follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        payload = response.json()
    companies: List[Dict[str, Any]] = []
    if isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, dict):
                companies.append(value)
    return companies


def resolve_company(query: str) -> Optional[CompanyIdentity]:
    normalized = query.strip()
    if not normalized:
        return None

    cik = _normalize_cik(normalized)
    if cik:
        for company in _company_index():
            if str(company.get("cik_str")) == cik:
                return CompanyIdentity(
                    cik=cik,
                    ticker=str(company.get("ticker") or "").upper() or None,
                    title=str(company.get("title") or company.get("name") or "").strip(),
                )

    upper = normalized.upper()
    for company in _company_index():
        ticker = str(company.get("ticker") or "").upper()
        title = str(company.get("title") or company.get("name") or "")
        if upper == ticker or normalized.lower() in title.lower():
            cik_value = _normalize_cik(company.get("cik_str"))
            if cik_value:
                return CompanyIdentity(cik=cik_value, ticker=ticker or None, title=title.strip())
    return None


def _get_json(url: str) -> Dict[str, Any]:
    with httpx.Client(timeout=30.0, headers=_headers(), follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.json()


def _recent_filings(submissions: Dict[str, Any]) -> List[Dict[str, Any]]:
    filings = submissions.get("filings", {})
    recent = filings.get("recent", {}) if isinstance(filings, dict) else {}
    if not isinstance(recent, dict):
        return []
    forms = recent.get("form", [])
    accession_numbers = recent.get("accessionNumber", [])
    primary_documents = recent.get("primaryDocument", [])
    primary_descriptions = recent.get("primaryDocDescription", [])
    filing_dates = recent.get("filingDate", [])
    report_dates = recent.get("reportDate", [])
    acceptance_dates = recent.get("acceptanceDateTime", [])
    act = recent.get("act", [])
    file_numbers = recent.get("fileNumber", [])
    film_numbers = recent.get("filmNumber", [])

    rows: List[Dict[str, Any]] = []
    for index, form in enumerate(forms):
        rows.append(
            {
                "form": form,
                "accession_number": accession_numbers[index]
                if index < len(accession_numbers)
                else None,
                "primary_document": primary_documents[index]
                if index < len(primary_documents)
                else None,
                "primary_doc_description": primary_descriptions[index]
                if index < len(primary_descriptions)
                else None,
                "filing_date": filing_dates[index] if index < len(filing_dates) else None,
                "report_date": report_dates[index] if index < len(report_dates) else None,
                "acceptance_date_time": acceptance_dates[index]
                if index < len(acceptance_dates)
                else None,
                "act": act[index] if index < len(act) else None,
                "file_number": file_numbers[index] if index < len(file_numbers) else None,
                "film_number": film_numbers[index] if index < len(film_numbers) else None,
            }
        )
    return rows


def _select_filings(
    company: CompanyIdentity,
    filing_types: Optional[Sequence[str]],
    limit: int,
) -> Dict[str, Any]:
    submissions = _get_json(_submission_url(company.cik))
    all_rows = _recent_filings(submissions)
    wanted = {form.upper() for form in filing_types} if filing_types else DEFAULT_FILING_TYPES
    results: List[Dict[str, Any]] = []
    for row in all_rows:
        if row["form"] not in wanted:
            continue
        accession = row.get("accession_number")
        primary_document = row.get("primary_document")
        if not accession or not primary_document:
            continue
        filing = {
            **row,
            "company_name": company.title,
            "ticker": company.ticker,
            "cik": company.cik,
            "document_url": _archive_path(company.cik, accession, primary_document),
        }
        results.append(filing)
        if len(results) >= limit:
            break
    return {
        "company": {
            "company_name": company.title,
            "ticker": company.ticker,
            "cik": company.cik,
        },
        "results": results,
    }


def search_filings(
    query: str,
    filing_types: Optional[Sequence[str]] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    company = resolve_company(query)
    if company is None:
        return {"error": f"Unable to resolve company or ticker: {query}"}
    capped_limit = max(1, min(limit, 20))
    payload = _select_filings(company, filing_types, capped_limit)
    payload["query"] = query
    payload["normalized_query"] = company.ticker or company.title
    return payload


def get_filing(
    query: str,
    filing_type: Optional[str] = None,
    accession_number: Optional[str] = None,
) -> Dict[str, Any]:
    company = resolve_company(query)
    if company is None:
        return {"error": f"Unable to resolve company or ticker: {query}"}
    submissions = _get_json(_submission_url(company.cik))
    all_rows = _recent_filings(submissions)
    wanted_form = filing_type.upper() if filing_type else None
    chosen: Optional[Dict[str, Any]] = None
    for row in all_rows:
        form = row.get("form")
        if wanted_form and form != wanted_form:
            continue
        if accession_number and row.get("accession_number") != accession_number:
            continue
        if row.get("accession_number") and row.get("primary_document"):
            chosen = row
            break
    if chosen is None:
        return {
            "error": (
                f"No filing found for {query}"
                + (f" ({filing_type})" if filing_type else "")
                + (f" accession {accession_number}" if accession_number else "")
            )
        }
    document_url = _archive_path(
        company.cik, chosen["accession_number"], chosen["primary_document"]
    )
    return {
        "company": {
            "company_name": company.title,
            "ticker": company.ticker,
            "cik": company.cik,
        },
        "filing": {
            **chosen,
            "document_url": document_url,
            "company_name": company.title,
            "ticker": company.ticker,
            "cik": company.cik,
        },
    }


def _html_to_text(raw_html: str) -> str:
    stripped = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw_html)
    stripped = re.sub(r"(?i)<br\s*/?>", "\n", stripped)
    stripped = re.sub(r"(?i)</(p|div|tr|li|h\d|section|table)>", "\n", stripped)
    stripped = re.sub(r"<[^>]+>", " ", stripped)
    stripped = html.unescape(stripped)
    stripped = re.sub(r"[ \t]+", " ", stripped)
    stripped = re.sub(r"\n{2,}", "\n", stripped)
    return stripped.strip()


def _fetch_text(url: str) -> str:
    with httpx.Client(timeout=30.0, headers=_headers(), follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return _html_to_text(response.text)


def _section_patterns(form: str) -> List[tuple[str, str]]:
    if form == "10-K":
        return [
            ("business", r"item\s+1\.?\s+business"),
            ("risk factors", r"item\s+1a\.?\s+risk factors"),
            ("unresolved staff comments", r"item\s+1b\.?\s+unresolved staff comments"),
            ("properties", r"item\s+2\.?\s+properties"),
            ("legal proceedings", r"item\s+3\.?\s+legal proceedings"),
            ("mine safety disclosures", r"item\s+4\.?\s+mine safety disclosures"),
            ("market for registrant common equity", r"item\s+5\.?"),
            ("selected financial data", r"item\s+6\.?\s+selected financial data"),
            (
                "management discussion and analysis",
                r"item\s+7\.?\s+management'?s discussion and analysis",
            ),
            (
                "quantitative and qualitative disclosures about market risk",
                r"item\s+7a\.?\s+quantitative and qualitative disclosures about market risk",
            ),
            ("financial statements", r"item\s+8\.?\s+financial statements"),
        ]
    if form == "10-Q":
        return [
            ("financial statements", r"item\s+1\.?\s+financial statements"),
            (
                "management discussion and analysis",
                r"item\s+2\.?\s+management'?s discussion and analysis",
            ),
            (
                "quantitative and qualitative disclosures about market risk",
                r"item\s+3\.?\s+quantitative and qualitative disclosures about market risk",
            ),
            ("controls and procedures", r"item\s+4\.?\s+controls and procedures"),
            ("other information", r"part\s+ii[\s\S]*item\s+1\.?\s+legal proceedings"),
        ]
    if form == "8-K":
        return [
            ("item 1.01", r"item\s+1\.01"),
            ("item 2.02", r"item\s+2\.02"),
            ("item 5.02", r"item\s+5\.02"),
            ("item 8.01", r"item\s+8\.01"),
            ("item 9.01", r"item\s+9\.01"),
        ]
    return []


def _extract_sections(text: str, form: str) -> List[Dict[str, Any]]:
    patterns = _section_patterns(form)
    if not patterns:
        return []

    matches: List[tuple[int, str, str]] = []
    for title, pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            matches.append((match.start(), title, pattern))

    matches.sort(key=lambda item: item[0])
    sections: List[Dict[str, Any]] = []
    for index, (start, title, _) in enumerate(matches):
        end = matches[index + 1][0] if index + 1 < len(matches) else len(text)
        section_text = text[start:end].strip()
        sections.append(
            {
                "section": title,
                "start": start,
                "end": end,
                "text": section_text,
            }
        )
    return sections


def _summarize_text(text: str, max_sentences: int = 3) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    summary = " ".join(
        sentence.strip() for sentence in sentences[:max_sentences] if sentence.strip()
    )
    return summary[:1200]


def _sentence_bullets(text: str, max_items: int = 5) -> List[str]:
    lines = [line.strip() for line in re.split(r"\n+", text) if line.strip()]
    bullets: List[str] = []
    for line in lines:
        if len(line) < 30:
            continue
        if any(
            keyword in line.lower()
            for keyword in (
                "risk",
                "material",
                "revenue",
                "expense",
                "liquidity",
                "cash",
                "debt",
                "litigation",
            )
        ):
            bullets.append(line[:220])
        if len(bullets) >= max_items:
            break
    if not bullets:
        bullets = [
            part[:220]
            for part in re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text))
            if part.strip()
        ][:max_items]
    return bullets


def get_filing_section(
    query: str,
    section: str,
    filing_type: Optional[str] = None,
    accession_number: Optional[str] = None,
) -> Dict[str, Any]:
    filing_payload = get_filing(
        query=query,
        filing_type=filing_type,
        accession_number=accession_number,
    )
    if "error" in filing_payload:
        return filing_payload
    filing = filing_payload["filing"]
    text = _fetch_text(filing["document_url"])
    sections = _extract_sections(text, filing["form"])
    normalized_target = section.strip().lower()
    for candidate in sections:
        if candidate["section"].lower() == normalized_target:
            return {
                **filing_payload,
                "section": candidate["section"],
                "section_text": candidate["text"],
                "sections": sections,
            }
    return {
        "error": f"Section not found: {section}",
        **filing_payload,
        "sections": sections,
    }


def summarize_filing_section(
    query: str,
    section: str,
    filing_type: Optional[str] = None,
    accession_number: Optional[str] = None,
) -> Dict[str, Any]:
    section_payload = get_filing_section(
        query=query,
        section=section,
        filing_type=filing_type,
        accession_number=accession_number,
    )
    if "error" in section_payload and "section_text" not in section_payload:
        return section_payload
    section_text = section_payload.get("section_text", "")
    summary = _summarize_text(section_text)
    bullets = _sentence_bullets(section_text)
    return {
        **section_payload,
        "summary": summary,
        "key_points": bullets,
        "section_char_count": len(section_text),
    }


class SecFilingService:
    """Small facade for tool handlers and future dependency injection."""

    def search_filings(
        self,
        query: str,
        filing_types: Optional[Sequence[str]] = None,
        limit: int = 5,
    ) -> Dict[str, Any]:
        return search_filings(query=query, filing_types=filing_types, limit=limit)

    def get_filing(
        self,
        query: str,
        filing_type: Optional[str] = None,
        accession_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        return get_filing(query=query, filing_type=filing_type, accession_number=accession_number)

    def get_filing_section(
        self,
        query: str,
        section: str,
        filing_type: Optional[str] = None,
        accession_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        return get_filing_section(
            query=query,
            section=section,
            filing_type=filing_type,
            accession_number=accession_number,
        )

    def summarize_filing_section(
        self,
        query: str,
        section: str,
        filing_type: Optional[str] = None,
        accession_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        return summarize_filing_section(
            query=query,
            section=section,
            filing_type=filing_type,
            accession_number=accession_number,
        )


sec_filing_service = SecFilingService()
