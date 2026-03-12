"""
Tool Result Memory Service

Bridges the gap between tool execution outputs and the memory promotion
pipeline.  After a financial tool runs, this service inspects the result,
extracts promotable facts (tickers, holdings, assumptions, screens), and
feeds them to MemoryPromotionService for gated long-term storage.

It also maintains a lightweight per-user "financial profile" — an
aggregate view of recently-used tickers, portfolio snapshots, valuation
assumptions, and screening criteria — stored as memory facts with the
special category ``financial_profile``.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from .memory_promotion_service import (
    MemoryPromotionService,
    PromotionCandidate,
    PromotionResult,
    memory_promotion_service,
)

logger = structlog.get_logger(__name__)

# Tool names that produce extractable financial facts
_FINANCIAL_TOOLS = {
    "dcf_calculator",
    "portfolio_analyzer",
    "earnings_summarizer",
    "stock_screener",
    "get_current_quote",
    "get_price_history",
    "get_financials",
    "get_earnings",
    "get_key_ratios",
}

# ── Extraction helpers ────────────────────────────────────────────


def _extract_dcf_facts(result: Dict[str, Any], args: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract promotable facts from a DCF calculator result."""
    facts: List[Dict[str, str]] = []
    ticker = args.get("ticker") or result.get("ticker", "???")

    valuation = result.get("valuation", {})
    assumptions = result.get("assumptions", {})

    intrinsic = valuation.get("intrinsic_value_per_share")
    upside = valuation.get("upside_percent")
    wacc = assumptions.get("wacc")
    growth = assumptions.get("growth_rate")

    if intrinsic is not None:
        facts.append({
            "content": (
                f"DCF valuation for {ticker}: intrinsic value ${intrinsic:.2f}/share "
                f"({'+' if upside and upside > 0 else ''}{upside:.1f}% vs current price)"
            ),
            "category": "instrument",
        })

    if wacc is not None and growth is not None:
        facts.append({
            "content": (
                f"DCF assumptions for {ticker}: WACC={wacc*100:.1f}%, "
                f"growth={growth*100:.1f}%, "
                f"projection_years={assumptions.get('projection_years', 5)}, "
                f"terminal_growth={assumptions.get('terminal_growth_rate', 0.025)*100:.1f}%"
            ),
            "category": "financial_profile",
        })

    return facts


def _extract_portfolio_facts(result: Dict[str, Any], args: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract promotable facts from a portfolio analysis result."""
    facts: List[Dict[str, str]] = []

    metrics = result.get("portfolio_metrics", {})
    holdings = result.get("holdings", [])

    # Summarise the portfolio composition
    if holdings:
        tickers = [h.get("ticker", "?") for h in holdings]
        facts.append({
            "content": f"Portfolio holdings analyzed: {', '.join(tickers)}",
            "category": "portfolio_action",
        })

    # Risk snapshot
    ann_ret = metrics.get("annualized_return")
    ann_vol = metrics.get("annualized_volatility")
    sharpe = metrics.get("sharpe_ratio")
    max_dd = metrics.get("max_drawdown")
    if ann_ret is not None and ann_vol is not None:
        facts.append({
            "content": (
                f"Portfolio risk snapshot: return={ann_ret*100:.1f}%, "
                f"volatility={ann_vol*100:.1f}%, "
                f"Sharpe={sharpe:.2f}, max drawdown={max_dd*100:.1f}%"
            ),
            "category": "risk_signal",
        })

    return facts


def _extract_earnings_facts(result: Dict[str, Any], args: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract promotable facts from an earnings summary result."""
    facts: List[Dict[str, str]] = []
    ticker = args.get("ticker") or result.get("ticker", "???")

    summary = result.get("summary", {})
    beats = summary.get("beats", 0)
    total = summary.get("total", 0)
    streak = summary.get("streak")

    if total > 0:
        facts.append({
            "content": (
                f"{ticker} earnings: {beats}/{total} beats"
                + (f", {streak}" if streak else "")
            ),
            "category": "instrument",
        })

    return facts


def _extract_screener_facts(result: Dict[str, Any], args: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract promotable facts from a stock screener result."""
    facts: List[Dict[str, str]] = []

    matches = result.get("matches", [])
    criteria = result.get("criteria_applied", {})

    if matches:
        tickers = [m.get("ticker", "?") for m in matches[:10]]
        facts.append({
            "content": f"Stock screen matched: {', '.join(tickers)} (criteria: {criteria})",
            "category": "financial_profile",
        })

    return facts


# Dispatcher mapping tool name → extractor function
_EXTRACTORS = {
    "dcf_calculator": _extract_dcf_facts,
    "portfolio_analyzer": _extract_portfolio_facts,
    "earnings_summarizer": _extract_earnings_facts,
    "stock_screener": _extract_screener_facts,
}


# ── Public API ────────────────────────────────────────────────────


async def extract_and_promote(
    tool_name: str,
    tool_args: Dict[str, Any],
    tool_result: Dict[str, Any],
    user_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
) -> List[PromotionResult]:
    """Inspect a tool result and promote any extractable financial facts.

    This is the main entry-point.  Call it after a successful tool execution
    inside the tool loop.

    Returns a list of :class:`PromotionResult` for observability.
    """
    if tool_name not in _EXTRACTORS:
        return []

    # Skip error results
    if "error" in tool_result:
        return []

    extractor = _EXTRACTORS[tool_name]
    raw_facts = extractor(tool_result, tool_args)

    if not raw_facts:
        return []

    results: List[PromotionResult] = []
    for fact in raw_facts:
        candidate = PromotionCandidate(
            content=fact["content"],
            category=fact["category"],
            source_conversation=conversation_id or "",
            source_type="tool_result",
            confidence=0.9,  # Tool outputs are high-confidence
            metadata={
                "user_id": user_id,
                "tool_name": tool_name,
                "tool_args": {k: v for k, v in tool_args.items() if isinstance(v, (str, int, float, bool))},
            },
            created_at=datetime.utcnow(),
        )
        try:
            result = await memory_promotion_service.evaluate_promotion_candidate(candidate)
            results.append(result)
        except Exception:
            logger.exception("tool_result_promotion_failed", tool=tool_name)

    logger.info(
        "tool_result_memory_extraction",
        tool=tool_name,
        facts_extracted=len(raw_facts),
        promoted=sum(1 for r in results if r.promoted),
    )
    return results


async def get_financial_profile(
    user_id: str,
    retrieval_svc=None,
) -> Dict[str, Any]:
    """Return a lightweight financial profile for *user_id*.

    Assembles recent ``financial_profile``, ``instrument``,
    ``portfolio_action``, and ``risk_signal`` memory facts into a
    structured dict the tool executor can inject as prior context.
    """
    if retrieval_svc is None:
        from .retrieval_service import retrieval_service as retrieval_svc

    profile: Dict[str, Any] = {
        "watched_tickers": [],
        "last_dcf_assumptions": {},
        "portfolio_snapshot": None,
        "recent_screens": [],
        "risk_snapshot": None,
    }

    try:
        facts = await retrieval_svc.retrieve_memory_facts(
            user_id=user_id,
            query="financial profile portfolio DCF assumptions",
            categories=[
                "financial_profile",
                "instrument",
                "portfolio_action",
                "risk_signal",
            ],
            k=15,
        )
    except Exception:
        logger.exception("get_financial_profile_failed", user_id=user_id)
        return profile

    for fact in facts:
        text = fact.get("fact_text", "")
        cat = fact.get("category", "")

        if cat == "financial_profile":
            if "DCF assumptions" in text:
                profile["last_dcf_assumptions"] = _parse_dcf_assumptions(text)
            elif "Stock screen matched" in text:
                profile["recent_screens"].append(text)
        elif cat == "instrument":
            tickers = re.findall(r"\b[A-Z]{1,5}\b", text)
            for t in tickers:
                if t not in profile["watched_tickers"]:
                    profile["watched_tickers"].append(t)
        elif cat == "portfolio_action":
            if "holdings analyzed" in text.lower():
                profile["portfolio_snapshot"] = text
        elif cat == "risk_signal":
            if "risk snapshot" in text.lower():
                profile["risk_snapshot"] = text

    return profile


def _parse_dcf_assumptions(text: str) -> Dict[str, Any]:
    """Parse a stored DCF-assumption fact back into a dict."""
    assumptions: Dict[str, Any] = {}
    wacc_m = re.search(r"WACC=([\d.]+)%", text)
    growth_m = re.search(r"growth=([\d.]+)%", text)
    years_m = re.search(r"projection_years=(\d+)", text)
    tg_m = re.search(r"terminal_growth=([\d.]+)%", text)
    ticker_m = re.search(r"for (\w+):", text)

    if ticker_m:
        assumptions["ticker"] = ticker_m.group(1)
    if wacc_m:
        assumptions["wacc"] = float(wacc_m.group(1)) / 100
    if growth_m:
        assumptions["growth_rate"] = float(growth_m.group(1)) / 100
    if years_m:
        assumptions["projection_years"] = int(years_m.group(1))
    if tg_m:
        assumptions["terminal_growth"] = float(tg_m.group(1)) / 100

    return assumptions
