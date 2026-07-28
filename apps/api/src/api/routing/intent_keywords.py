"""
Keyword anchor sets, scoring helpers, and the softmax utility for intent
classification.

Extracted from intent_classifier.py for modularity.
"""

from __future__ import annotations

import math
import re
from typing import Dict, List, Tuple

from .intent_models import IntentLabel

# ---------------------------------------------------------------------------
# Keyword anchor sets — weighted tuples: (keyword, weight)
# Higher weight = stronger signal for that label.
# ---------------------------------------------------------------------------

_CODING_KEYWORDS: List[Tuple[str, float]] = [
    ("write a function", 1.0),
    ("write me a function", 1.0),
    ("implement a", 0.9),
    ("implement the", 0.8),
    ("create a class", 1.0),
    ("write code", 1.0),
    ("write a script", 0.9),
    ("write a program", 0.9),
    ("debug this", 1.0),
    ("debugging", 0.8),
    ("refactor", 0.9),
    ("refactor this", 1.0),
    ("pull request", 0.9),
    ("code review", 1.0),
    ("find the bug", 1.0),
    ("fix the bug", 1.0),
    ("unit test", 0.9),
    ("write tests", 0.9),
    ("test coverage", 0.8),
    ("in python", 0.8),
    ("in typescript", 0.8),
    ("in javascript", 0.8),
    ("in golang", 0.8),
    ("in rust", 0.8),
    ("in java", 0.8),
    ("in c++", 0.8),
    # Standalone language names — lower weight, catch "Python function" etc.
    ("python function", 0.9),
    ("typescript code", 0.9),
    ("javascript code", 0.9),
    ("python code", 0.9),
    ("python script", 0.9),
    ("python", 0.5),
    ("typescript", 0.5),
    ("javascript", 0.5),
    ("sql query", 0.9),
    ("api endpoint", 0.9),
    ("rest api", 0.8),
    # Error types
    ("typeerror", 0.9),
    ("nameerror", 0.9),
    ("attributeerror", 0.9),
    ("type error", 0.8),
    ("syntax error", 0.9),
    ("import error", 0.8),
    ("stacktrace", 0.9),
    ("stack trace", 0.9),
    ("exception", 0.7),
    ("lgtm", 0.7),
    ("dockerfile", 0.9),
    ("makefile", 0.8),
]

_RESEARCH_KEYWORDS: List[Tuple[str, float]] = [
    ("research", 0.7),
    ("literature review", 1.0),
    ("academic paper", 1.0),
    ("summarize this article", 1.0),
    ("summarize the", 0.7),
    ("find sources", 0.9),
    ("what is the evidence", 1.0),
    ("cite", 0.7),
    ("citation", 0.8),
    ("according to", 0.7),
    ("studies show", 0.9),
    ("meta-analysis", 1.0),
    ("background on", 0.8),
    ("overview of", 0.7),
    ("explain the concept", 0.8),
    ("what does the research say", 1.0),
    ("investigate", 0.8),
    ("explore the topic", 0.9),
    ("key findings", 0.8),
    ("state of the art", 0.9),
    ("prior work", 0.9),
    ("what are the main theories", 0.9),
    ("compare these papers", 0.9),
]

_CREATIVE_KEYWORDS: List[Tuple[str, float]] = [
    ("write a story", 1.0),
    ("write me a story", 1.0),
    ("write a poem", 1.0),
    ("write a blog post", 1.0),
    ("draft a", 0.8),
    ("creative writing", 1.0),
    ("short story", 0.9),
    ("fiction", 0.8),
    ("narrative", 0.8),
    ("character development", 0.9),
    ("plot outline", 0.9),
    ("screenplay", 1.0),
    ("song lyrics", 1.0),
    ("write lyrics", 1.0),
    ("haiku", 1.0),
    ("limerick", 1.0),
    ("metaphor", 0.7),
    ("tone of voice", 0.8),
    ("write in the style of", 1.0),
    ("creative brief", 0.9),
    ("write a caption", 0.8),
    ("tagline", 0.8),
    ("slogan", 0.8),
    ("world-building", 0.9),
    ("brainstorm ideas for a story", 1.0),
]

_BUSINESS_KEYWORDS: List[Tuple[str, float]] = [
    ("business strategy", 1.0),
    ("go-to-market", 1.0),
    ("gtm", 0.9),
    ("market analysis", 1.0),
    ("competitive analysis", 1.0),
    ("pitch deck", 1.0),
    ("investor pitch", 1.0),
    ("product roadmap", 0.9),
    ("okr", 0.9),
    ("kpi", 0.8),
    ("revenue model", 1.0),
    ("monetization", 0.9),
    ("customer acquisition", 0.9),
    ("churn", 0.8),
    ("unit economics", 1.0),
    ("stakeholder", 0.8),
    ("executive summary", 0.9),
    ("board deck", 1.0),
    ("marketing campaign", 0.9),
    ("brand positioning", 0.9),
    ("swot", 1.0),
    ("market size", 0.9),
    ("tam", 0.9),
    ("sam", 0.8),
    ("som", 0.8),
    ("business plan", 1.0),
    ("launch strategy", 1.0),
    ("hiring plan", 0.8),
]

_FINANCE_KEYWORDS: List[Tuple[str, float]] = [
    ("stock", 0.8),
    ("stocks", 0.8),
    ("equity", 0.8),
    ("portfolio", 0.9),
    ("var", 0.8),
    ("value at risk", 1.0),
    ("cvar", 1.0),
    ("expected shortfall", 1.0),
    ("alpha", 0.7),
    ("beta", 0.7),
    ("sharpe ratio", 1.0),
    ("drawdown", 0.9),
    ("p&l", 1.0),
    ("pnl", 1.0),
    ("return on investment", 0.9),
    ("roi", 0.7),
    ("hedge", 0.9),
    ("hedging", 0.9),
    ("long/short", 1.0),
    ("short selling", 1.0),
    ("derivative", 0.9),
    ("options", 0.8),
    ("futures", 0.8),
    ("swap", 0.8),
    ("yield curve", 1.0),
    ("interest rate", 0.8),
    ("credit risk", 0.9),
    ("dividend", 0.9),
    ("earnings", 0.8),
    ("eps", 0.8),
    ("pe ratio", 0.9),
    ("asset allocation", 1.0),
    ("rebalancing", 0.9),
    ("trading strategy", 1.0),
    ("backtesting", 0.9),
    ("technical analysis", 0.9),
    ("fundamental analysis", 0.9),
    ("market cap", 0.8),
    ("liquidity", 0.7),
    ("volatility", 0.8),
]

_REASONING_KEYWORDS: List[Tuple[str, float]] = [
    ("think step by step", 1.0),
    ("reason about", 0.9),
    ("step by step", 0.8),
    ("pros and cons", 1.0),
    ("pros/cons", 1.0),
    ("tradeoffs", 0.9),
    ("trade-offs", 0.9),
    ("weigh the options", 1.0),
    ("should i", 0.7),
    ("help me decide", 0.9),
    ("what would happen if", 0.9),
    ("logical consequence", 1.0),
    ("first principles", 1.0),
    ("socratic", 0.9),
    ("devil's advocate", 1.0),
    ("what are the implications", 0.9),
    ("evaluate", 0.7),
    ("assess", 0.7),
    ("compare and contrast", 1.0),
    ("critically analyze", 1.0),
    ("what is the best approach", 0.8),
    ("make a case for", 0.9),
    ("logical argument", 0.9),
    ("inductive reasoning", 1.0),
    ("deductive", 0.9),
    ("is this valid", 0.8),
    ("fallacy", 0.9),
    ("assumption", 0.7),
]

_AGENT_TASK_KEYWORDS: List[Tuple[str, float]] = [
    ("execute", 0.8),
    ("automate", 0.9),
    ("run this script", 1.0),
    ("schedule a task", 1.0),
    ("set up a cron", 1.0),
    ("trigger a", 0.9),
    ("fetch data from", 0.9),
    ("scrape", 0.9),
    ("web scraping", 1.0),
    ("send an email", 1.0),
    ("send a message", 0.8),
    ("post to", 0.8),
    ("deploy", 0.9),
    ("build and deploy", 1.0),
    ("ci/cd", 1.0),
    ("pipeline", 0.8),
    ("workflow", 0.8),
    ("orchestrate", 0.9),
    ("call this api", 1.0),
    ("hit the api", 0.9),
    ("make a request to", 0.8),
    ("loop through", 0.9),
    ("batch process", 1.0),
    ("process these files", 1.0),
    ("search the web", 0.9),
    ("look up", 0.7),
    ("use a tool", 0.9),
    ("agent", 0.7),
    ("agentic", 1.0),
    ("multi-step task", 1.0),
    ("do this for me automatically", 1.0),
]

# Priority-ordered list: label, keywords, minimum weight threshold to count a hit
LABEL_CONFIGS: List[Tuple[IntentLabel, List[Tuple[str, float]]]] = [
    (IntentLabel.AGENT_TASK, _AGENT_TASK_KEYWORDS),
    (IntentLabel.CODING, _CODING_KEYWORDS),
    (IntentLabel.FINANCE, _FINANCE_KEYWORDS),
    (IntentLabel.BUSINESS, _BUSINESS_KEYWORDS),
    (IntentLabel.CREATIVE, _CREATIVE_KEYWORDS),
    (IntentLabel.REASONING, _REASONING_KEYWORDS),
    (IntentLabel.RESEARCH, _RESEARCH_KEYWORDS),
]

# Code syntax detector: 3+ code-syntax tokens → strong CODING signal
CODE_SYNTAX_RE = re.compile(
    r"(def |function |const |let |var |import |from |class |public |private |return |async |await |lambda )"
)


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------


def score_label(text: str, keywords: List[Tuple[str, float]]) -> float:
    """Return a cumulative weighted score for how well text matches a label."""
    score = 0.0
    for kw, weight in keywords:
        if kw in text:
            score += weight
    return score


def softmax_confidence(scores: Dict[IntentLabel, float]) -> Dict[IntentLabel, float]:
    """Convert raw scores to probabilities via softmax (temperature=1.5 for sharper peaks)."""
    temperature = 1.5
    values = list(scores.values())
    max_val = max(values) if values else 0.0
    exp_vals = {k: math.exp((v - max_val) / temperature) for k, v in scores.items()}
    total = sum(exp_vals.values()) or 1.0
    return {k: v / total for k, v in exp_vals.items()}


def cosine(a: List[float], b: List[float]) -> float:
    """Cosine similarity (pure stdlib — no numpy required)."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


__all__ = [
    "LABEL_CONFIGS",
    "CODE_SYNTAX_RE",
    "score_label",
    "softmax_confidence",
    "cosine",
]
