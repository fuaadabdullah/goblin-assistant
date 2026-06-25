"""Market news summarizer skill."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Optional

from ...services.financial_data_service import (
    financial_data_service,
    normalize_market_news_sources,
)
from ...services.financial_guardrails import safe_skill
from ..registry import ToolDefinition, ToolParameter, register_tool

_POSITIVE_MARKERS = (
    "beat",
    "beats",
    "upgrade",
    "raises",
    "raised",
    "growth",
    "rally",
    "surge",
    "record",
    "approval",
    "contract",
    "bull",
)
_NEGATIVE_MARKERS = (
    "miss",
    "misses",
    "cut",
    "cuts",
    "downgrade",
    "downgrades",
    "lawsuit",
    "probe",
    "investigation",
    "layoff",
    "layoffs",
    "drop",
    "drops",
    "decline",
    "declines",
    "slump",
)
_THEME_KEYWORDS = {
    "earnings": ("earnings", "quarter", "guidance", "revenue", "profit"),
    "analyst": ("analyst", "upgrade", "downgrade", "price target", "coverage"),
    "regulation": ("regulation", "regulatory", "antitrust", "probe", "investigation"),
    "product": ("launch", "product", "chip", "device", "platform"),
    "macro": ("rates", "inflation", "fed", "tariff", "macro", "economy"),
    "m&a": ("acquire", "acquisition", "merger", "deal", "buyout"),
    "jobs": ("layoff", "layoffs", "hiring", "headcount", "job cuts"),
}


async def _normalize_sources(
    *,
    ticker: Optional[str],
    query: Optional[str],
    sources: Optional[List[Dict[str, Any]]],
    limit: int,
) -> Dict[str, Any]:
    if sources is not None:
        normalized_query = query or ticker or ""
        normalized = normalize_market_news_sources(normalized_query, sources[:limit])
        return normalized

    if ticker:
        payload = await financial_data_service.get_market_news(ticker, limit)
    elif query:
        payload = await financial_data_service.get_market_news(query, limit)
    else:
        raise ValueError("ticker or query is required when sources are not provided")

    return payload


def _flatten_texts(sources: Iterable[Dict[str, Any]]) -> str:
    parts: List[str] = []
    for source in sources:
        parts.append(str(source.get("title", "")))
        parts.append(str(source.get("snippet", "")))
    return " ".join(parts).lower()


def _score_sentiment(text: str) -> Dict[str, Any]:
    positive = sum(text.count(marker) for marker in _POSITIVE_MARKERS)
    negative = sum(text.count(marker) for marker in _NEGATIVE_MARKERS)
    score = positive - negative
    if score > 0:
        label = "positive"
    elif score < 0:
        label = "negative"
    else:
        label = "neutral"
    return {
        "label": label,
        "score": score,
        "positive_signals": positive,
        "negative_signals": negative,
    }


def _detect_themes(text: str) -> List[str]:
    themes: List[str] = []
    for theme, keywords in _THEME_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            themes.append(theme)
    return themes


def _build_highlights(sources: List[Dict[str, Any]], max_items: int) -> List[str]:
    highlights: List[str] = []
    for source in sources[:max_items]:
        title = str(source.get("title", "")).strip()
        snippet = str(source.get("snippet", "")).strip()
        publisher = str(source.get("publisher", "")).strip()
        if not title:
            continue
        if snippet and snippet != title:
            highlights.append(f"{title} - {snippet[:140]}")
        elif publisher:
            highlights.append(f"{title} ({publisher})")
        else:
            highlights.append(title)
    return highlights


@safe_skill
async def _handle_news_summarizer(
    ticker: Optional[str] = None,
    query: Optional[str] = None,
    sources: Optional[List[Dict[str, Any]]] = None,
    max_items: int = 6,
) -> Dict[str, Any]:
    """Summarize normalized market news for a ticker or topic."""

    limit = max(1, min(int(max_items), 10))
    normalized = await _normalize_sources(
        ticker=ticker.strip().upper() if ticker else None,
        query=query.strip() if query else None,
        sources=sources,
        limit=limit,
    )

    normalized_sources = list(normalized.get("results", []))[:limit]
    normalized_query = normalized.get("normalized_query") or query or ticker or ""
    normalized_ticker = normalized.get("ticker")

    text_blob = _flatten_texts(normalized_sources)
    sentiment = _score_sentiment(text_blob)
    themes = _detect_themes(text_blob)
    publisher_counts = Counter(
        source.get("publisher") or "Unknown" for source in normalized_sources
    )

    if normalized_ticker is None and ticker:
        normalized_ticker = ticker.strip().upper()

    if normalized_ticker:
        summary_head = f"{normalized_ticker}: "
    elif normalized_query:
        summary_head = f"{normalized_query}: "
    else:
        summary_head = "Market news: "

    if normalized_sources:
        summary_body = (
            f"{len(normalized_sources)} headline(s) from {len(publisher_counts)} publisher(s)."
        )
        if themes:
            summary_body += f" Main themes: {', '.join(themes[:4])}."
        summary_body += f" Sentiment looks {sentiment['label']}."
    else:
        summary_body = "No market news sources were available."

    return {
        "ticker": normalized_ticker,
        "query": normalized.get("query") or query or ticker or "",
        "normalized_query": normalized_query,
        "source_count": len(normalized_sources),
        "publisher_counts": dict(
            sorted(publisher_counts.items(), key=lambda item: item[1], reverse=True)
        ),
        "themes": themes,
        "sentiment": sentiment,
        "headline_highlights": _build_highlights(normalized_sources, max_items=limit),
        "summary": summary_head + summary_body,
        "sources": normalized_sources,
    }


register_tool(
    ToolDefinition(
        name="news_summarizer",
        description=(
            "Use when the user wants a concise synthesis of recent market news "
            "for a ticker or financial topic. The tool normalizes news sources, "
            "groups headlines by publisher, identifies themes, and produces a "
            "simple sentiment readout from the latest headlines."
        ),
        parameters=[
            ToolParameter(
                name="ticker",
                type="string",
                description=(
                    "Public equity ticker symbol to summarize, such as AAPL or NVDA. "
                    "Optional when query or sources are provided."
                ),
                required=False,
                default=None,
            ),
            ToolParameter(
                name="query",
                type="string",
                description=(
                    "Free-form news topic or query. Optional when ticker or sources are provided."
                ),
                required=False,
                default=None,
            ),
            ToolParameter(
                name="sources",
                type="array",
                description=(
                    "Optional pre-fetched news articles to summarize. Each item may "
                    "include title, url, snippet, publisher, and published_at fields."
                ),
                required=False,
                items={"type": "object"},
                default=None,
            ),
            ToolParameter(
                name="max_items",
                type="integer",
                description="Maximum number of articles to summarize (1-10). Defaults to 6.",
                required=False,
                default=6,
            ),
        ],
        handler=_handle_news_summarizer,
        category="finance",
    )
)
