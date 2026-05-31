"""
Lightweight research orchestration tool for Goblin Assistant.

Builds concise cited briefs by combining existing web and academic search tools.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit

from .academic_search import _handle_academic_search
from .web_search import _handle_web_search
from api.services.pdf_extraction_service import (
    DEFAULT_MAX_CONTEXT_CHARS,
    extract_pdf,
    select_relevant_chunks,
)
from ..registry import ToolDefinition, ToolParameter, register_tool

MAX_SOURCES_CAP = 10
MAX_PDF_CHUNKS_CAP = 12
_KNOWN_ACADEMIC_DOMAINS = {
    "arxiv.org",
    "semanticscholar.org",
    "doi.org",
    "acm.org",
    "ieee.org",
    "springer.com",
    "nature.com",
    "sciencedirect.com",
    "openreview.net",
}
_DATE_PREFIX_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?")


def _get_base_dir() -> Path:
    raw = os.environ.get("GOBLIN_FILE_WORKSPACE", "~/goblin-workspace")
    return Path(raw).expanduser().resolve()


def _resolve_path(user_path: str) -> Path:
    base = _get_base_dir()
    candidate = (base / user_path).resolve()
    if base not in candidate.parents and candidate != base:
        raise ValueError(
            f"Path '{user_path}' resolves outside the workspace. "
            "All research PDF operations must stay within the goblin workspace."
        )
    return candidate


def _to_source_items(raw_items: List[Dict[str, Any]], source_type: str) -> List[Dict[str, str]]:
    normalized: List[Dict[str, str]] = []
    for item in raw_items:
        title = str(item.get("title", "")).strip()
        url = str(item.get("url", "")).strip()
        snippet = str(item.get("snippet") or item.get("abstract") or "").strip()
        if not title and not url:
            continue
        normalized.append(
            {
                "title": title,
                "url": url,
                "snippet": snippet,
                "source_type": source_type,
            }
        )
    return normalized


def _build_findings(query: str, sources: List[Dict[str, str]]) -> List[str]:
    findings: List[str] = []
    if not sources:
        return [f"No high-confidence sources were found for '{query}'."]

    findings.append(f"Collected {len(sources)} sources for '{query}'.")
    unique_domains = len({s.get("url", "").split("/")[2] for s in sources if "://" in s.get("url", "")})
    findings.append(f"Coverage spans {unique_domains} distinct source domains.")

    for source in sources[:3]:
        title = source.get("title", "").strip() or "Untitled source"
        snippet = source.get("snippet", "").strip()
        summary = snippet[:180].rstrip() if snippet else "No summary snippet available."
        findings.append(f"{title}: {summary}")
    return findings[:5]


def _parse_domain(url: str) -> Optional[str]:
    try:
        parsed = urlsplit(url.strip())
    except Exception:  # noqa: BLE001
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    domain = parsed.netloc.lower().strip()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def _looks_like_iso_date(value: str) -> bool:
    raw = value.strip()
    if not raw:
        return False
    if _DATE_PREFIX_RE.match(raw) is None:
        return False
    # Accept YYYY-MM and YYYY-MM-DD quickly, otherwise try ISO parse.
    if len(raw) in {7, 10}:
        return True
    try:
        datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


async def _handle_verify_sources(
    sources: List[Dict[str, Any]],
    strictness: str = "standard",
) -> Dict[str, Any]:
    if strictness not in {"lenient", "standard"}:
        return {"error": "strictness must be 'lenient' or 'standard'"}

    verified_sources: List[Dict[str, Any]] = []
    seen_url: Dict[str, int] = {}
    seen_title: Dict[str, int] = {}

    for idx, source in enumerate(sources):
        if not isinstance(source, dict):
            verified_sources.append(
                {
                    "index": idx,
                    "source": source,
                    "verification": {
                        "confidence": 0.0,
                        "domain": None,
                        "issues": ["malformed_source_object"],
                        "warnings": [],
                    },
                }
            )
            continue

        title = str(source.get("title", "")).strip()
        url = str(source.get("url", "")).strip()
        source_type = str(source.get("source_type", "other")).strip().lower() or "other"
        published_at = str(source.get("published_at", "")).strip()
        issues: List[str] = []
        warnings: List[str] = []
        confidence = 1.0

        if not title:
            issues.append("missing_title")
            confidence -= 0.2
        if not url:
            issues.append("missing_url")
            confidence -= 0.3

        domain = _parse_domain(url) if url else None
        if url and not domain:
            issues.append("malformed_url")
            confidence -= 0.35

        if source_type not in {"web", "academic", "pdf", "other"}:
            issues.append("unknown_source_type")
            confidence -= 0.15

        if published_at:
            if not _looks_like_iso_date(published_at):
                warnings.append("published_at_not_iso_like")
                confidence -= 0.05
        elif strictness == "standard":
            warnings.append("missing_published_at")
            confidence -= 0.05

        if domain and source_type == "academic" and not any(
            domain.endswith(d) for d in _KNOWN_ACADEMIC_DOMAINS
        ):
            warnings.append("academic_source_domain_unrecognized")
            confidence -= 0.07
        if domain and source_type == "web" and any(
            domain.endswith(d) for d in _KNOWN_ACADEMIC_DOMAINS
        ):
            warnings.append("web_source_points_to_academic_domain")
            confidence -= 0.03

        if url:
            norm_url = url.rstrip("/").lower()
            if norm_url in seen_url:
                warnings.append(f"duplicate_url_with_index_{seen_url[norm_url]}")
                confidence -= 0.12
            else:
                seen_url[norm_url] = idx

        if title:
            norm_title = title.lower().strip()
            if norm_title in seen_title:
                warnings.append(f"duplicate_title_with_index_{seen_title[norm_title]}")
                confidence -= 0.05
            else:
                seen_title[norm_title] = idx

        confidence = max(0.0, min(1.0, round(confidence, 3)))
        verified_sources.append(
            {
                "index": idx,
                "source": {
                    "title": title,
                    "url": url,
                    "source_type": source_type,
                    "published_at": published_at or None,
                },
                "verification": {
                    "confidence": confidence,
                    "domain": domain,
                    "issues": issues,
                    "warnings": warnings,
                },
            }
        )

    min_confidence = 0.6 if strictness == "lenient" else 0.7
    verified_count = sum(
        1
        for item in verified_sources
        if item["verification"]["confidence"] >= min_confidence
        and "malformed_url" not in item["verification"]["issues"]
        and "missing_url" not in item["verification"]["issues"]
    )
    summary = {
        "strictness": strictness,
        "total_sources": len(verified_sources),
        "verified_sources": verified_count,
        "flagged_sources": len(verified_sources) - verified_count,
        "average_confidence": round(
            sum(item["verification"]["confidence"] for item in verified_sources)
            / max(1, len(verified_sources)),
            3,
        ),
    }

    return {"summary": summary, "verified_sources": verified_sources}


async def _handle_research_pdf_extract(
    path: str,
    query: Optional[str] = None,
    max_chunks: int = 5,
) -> Dict[str, Any]:
    capped_chunks = max(1, min(max_chunks, MAX_PDF_CHUNKS_CAP))

    try:
        resolved = _resolve_path(path)
    except ValueError as exc:
        return {"error": str(exc)}

    if not resolved.exists():
        return {"error": f"PDF not found: {path}"}
    if not resolved.is_file():
        return {"error": f"Path is not a file: {path}"}
    if resolved.suffix.lower() != ".pdf":
        return {"error": f"Path is not a PDF file: {path}"}

    extracted = extract_pdf(str(resolved))
    chunks = extracted.get("chunks", [])
    if not isinstance(chunks, list):
        chunks = []

    if query and query.strip():
        selected_chunks = select_relevant_chunks(
            query=query,
            chunks=chunks,
            max_chunks=capped_chunks,
            max_chars=DEFAULT_MAX_CONTEXT_CHARS,
        )
    else:
        selected_chunks = chunks[:capped_chunks]

    return {
        "path": str(resolved),
        "pdf_extraction_status": extracted.get("pdf_extraction_status"),
        "page_count": extracted.get("page_count", 0),
        "char_count": extracted.get("char_count", 0),
        "total_chunks": len(chunks),
        "selected_chunks": selected_chunks,
        "selected_count": len(selected_chunks),
        "warnings": extracted.get("warnings", []),
        "ocr_attempted": extracted.get("ocr_attempted", False),
    }


async def _handle_lightweight_research(
    query: str,
    max_sources: int = 6,
    include_academic: bool = True,
    include_web: bool = True,
) -> Dict[str, Any]:
    if not query.strip():
        return {"error": "query must be non-empty"}
    if not include_academic and not include_web:
        return {"error": "At least one of include_academic/include_web must be true"}

    max_sources = max(1, min(max_sources, MAX_SOURCES_CAP))
    coverage: Dict[str, Any] = {
        "requested": {
            "include_web": include_web,
            "include_academic": include_academic,
            "max_sources": max_sources,
        },
        "providers": {},
        "partial_failures": [],
    }

    sources: List[Dict[str, str]] = []

    if include_web:
        web_result = await _handle_web_search(query=query, max_results=max_sources)
        if "error" in web_result:
            coverage["partial_failures"].append({"provider": "web_search", "error": web_result["error"]})
            coverage["providers"]["web_search"] = {"ok": False, "count": 0}
        else:
            web_sources = _to_source_items(web_result.get("results", []), source_type="web")
            coverage["providers"]["web_search"] = {"ok": True, "count": len(web_sources)}
            sources.extend(web_sources)

    if include_academic:
        acad_result = await _handle_academic_search(query=query, source="arxiv", max_results=max_sources)
        if "error" in acad_result:
            coverage["partial_failures"].append(
                {"provider": "academic_search", "error": acad_result["error"]}
            )
            coverage["providers"]["academic_search"] = {"ok": False, "count": 0}
        else:
            acad_sources = _to_source_items(acad_result.get("results", []), source_type="academic")
            coverage["providers"]["academic_search"] = {"ok": True, "count": len(acad_sources)}
            sources.extend(acad_sources)

    if not sources and coverage["partial_failures"]:
        return {
            "error": "All requested research providers failed",
            "coverage": coverage,
        }

    sources = sources[:max_sources]
    findings = _build_findings(query=query, sources=sources)
    brief = (
        f"Lightweight research brief for '{query}': "
        f"{len(sources)} sources reviewed across {len(coverage['providers'])} provider paths."
    )

    return {
        "query": query,
        "brief": brief,
        "findings": findings,
        "sources": sources,
        "coverage": coverage,
    }


register_tool(
    ToolDefinition(
        name="lightweight_research",
        description=(
            "Use when the user asks for quick topical research with citations. "
            "Combines web and academic search, then returns a concise brief, "
            "key findings, and normalized source links."
        ),
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description="Research question or topic to investigate.",
            ),
            ToolParameter(
                name="max_sources",
                type="integer",
                description="Maximum sources in output (1-10). Defaults to 6.",
                required=False,
                default=6,
            ),
            ToolParameter(
                name="include_academic",
                type="boolean",
                description="Include academic search results. Defaults to true.",
                required=False,
                default=True,
            ),
            ToolParameter(
                name="include_web",
                type="boolean",
                description="Include web search results. Defaults to true.",
                required=False,
                default=True,
            ),
        ],
        handler=_handle_lightweight_research,
        category="research",
    )
)

register_tool(
    ToolDefinition(
        name="verify_sources",
        description=(
            "Verify research source metadata and consistency. Checks URL/domain shape, "
            "duplicate sources, source-type consistency, and metadata completeness, then "
            "returns confidence and verification flags. This is metadata verification only, "
            "not claim-level fact adjudication."
        ),
        parameters=[
            ToolParameter(
                name="sources",
                type="array",
                description="Array of source objects to verify.",
                items={"type": "object"},
            ),
            ToolParameter(
                name="strictness",
                type="string",
                description="Verification strictness level.",
                required=False,
                enum=["lenient", "standard"],
                default="standard",
            ),
        ],
        handler=_handle_verify_sources,
        category="research",
    )
)

register_tool(
    ToolDefinition(
        name="research_pdf_extract",
        description=(
            "Read-only PDF extraction helper for research workflows. Extracts text chunks "
            "from a PDF in the goblin workspace and returns either query-relevant chunks "
            "or top chunks when no query is provided."
        ),
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="PDF file path relative to the goblin workspace root.",
            ),
            ToolParameter(
                name="query",
                type="string",
                description="Optional relevance query for chunk selection.",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="max_chunks",
                type="integer",
                description="Maximum chunks to return (1-12). Defaults to 5.",
                required=False,
                default=5,
            ),
        ],
        handler=_handle_research_pdf_extract,
        category="research",
    )
)
