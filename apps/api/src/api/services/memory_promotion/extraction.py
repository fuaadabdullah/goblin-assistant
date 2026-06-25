import re
from datetime import datetime
from typing import List, Optional

from .models import PromotionCandidate

EDUCATION_SIGNALS = [
    "studying",
    "learning",
    "explain",
    "understand",
    "confused",
    "CFA",
    "CPA",
    "exam",
    "course",
    "class",
    "professor",
    "GSU",
    "finance major",
    "homework",
    "assignment",
]

_PREFERENCE_PATTERNS = [
    r"\b(i prefer|i like|i love|i always use|i consistently use)\b",
    r"\b(communication|style|tooling|model|privacy|security)\b",
    r"\b(concise|detailed|technical|simple|clear)\b",
]
_FACT_PATTERNS = [
    r"\b(project|system|role|constraint|objective|goal|requirement)\b",
    r"\b(building|developing|working on|maintaining)\b",
    r"\b(team|company|organization|client)\b",
]
_IDENTITY_PATTERNS = [
    r"\b(values|principles|beliefs|philosophy|approach)\b",
    r"\b(rigorous|thorough|methodical|systematic)\b",
]
_EMOTIONAL_DISQUALIFIERS = [
    r"\b(feeling|stressed|frustrated|excited|today|right now|currently)\b",
    r"\b(i think|i believe|i feel)\b",
    r"\b(should|must|have to|need to)\b",
    r"\b(lol|joke|funny|complain|annoyed)\b",
]
_INSTRUMENT_PATTERNS = [
    r"\b(ticker|stock|equity|bond|etf|fund|option|futures|commodity)\b",
    r"\b(asset class|fixed income|equities|derivatives|forex|crypto)\b",
    r"\b(s&p\s*500|nasdaq|dow\s*jones|russell|msci|ftse)\b",
    r"\b(treasury|t-bill|municipal|corporate bond)\b",
    r"\b(shares of|position in|exposure to|holding in)\b",
]
_RISK_SIGNAL_PATTERNS = [
    r"\b(volatility|vol|vix|beta|alpha|sharpe|sortino)\b",
    r"\b(drawdown|value.at.risk|var|cvar|expected\s*shortfall)\b",
    r"\b(correlation|covariance|standard\s*deviation|risk.adjusted)\b",
    r"\b(stress\s*test|scenario\s*analysis|monte\s*carlo|back\s*test)\b",
    r"\b(tail\s*risk|downside|hedge)\b",
]
_REGULATORY_PATTERNS = [
    r"\b(sec|finra|cftc|occ|fca|esma|mifid)\b",
    r"\b(compliance|fiduciary|suitability|kyc|aml)\b",
    r"\b(dodd.frank|volcker|basel|sarbanes.oxley|sox)\b",
    r"\b(insider\s*trading|material\s*non.public|mnpi)\b",
    r"\b(prospectus|disclosure|filing|10-[kq])\b",
]
_PORTFOLIO_ACTION_PATTERNS = [
    r"\b(rebalance|reallocate|liquidate|accumulate|trim)\b",
    r"\b(buy|sell|short|cover|exercise|roll)\b.*\b(position|shares)\b",
    r"\b(target\s*allocation|overweight|underweight)\b",
    r"\b(stop.loss|take.profit|limit\s*order|market\s*order)\b",
    r"\b(tax.loss\s*harvest|wash\s*sale|lot\s*selection)\b",
]
_MACRO_EVENT_PATTERNS = [
    r"\b(fomc|fed\s*meeting|rate\s*decision|rate\s*hike|rate\s*cut)\b",
    r"\b(cpi|ppi|pce|inflation|deflation|stagflation)\b",
    r"\b(gdp|unemployment|non.?farm\s*payroll|nfp|jobs\s*report)\b",
    r"\b(earnings|eps|revenue\s*beat|revenue\s*miss|guidance)\b",
    r"\b(yield\s*curve|inversion|recession|taper)\b",
]


def classify_memory_category(content: str) -> Optional[str]:
    """
    Return the memory category for *content*, or None if ineligible.

    Disqualifies emotional/temporary language first, then pattern-matches
    into: preference, fact, identity_trait, instrument, risk_signal,
    regulatory_constraint, portfolio_action, macro_event, education_context.
    """
    content_lower = content.lower().strip()

    for pattern in _EMOTIONAL_DISQUALIFIERS:
        if re.search(pattern, content_lower):
            return None

    for pattern in _PREFERENCE_PATTERNS:
        if re.search(pattern, content_lower):
            return "preference"
    for pattern in _FACT_PATTERNS:
        if re.search(pattern, content_lower):
            return "fact"
    for pattern in _IDENTITY_PATTERNS:
        if re.search(pattern, content_lower):
            return "identity_trait"
    for pattern in _INSTRUMENT_PATTERNS:
        if re.search(pattern, content_lower):
            return "instrument"
    for pattern in _RISK_SIGNAL_PATTERNS:
        if re.search(pattern, content_lower):
            return "risk_signal"
    for pattern in _REGULATORY_PATTERNS:
        if re.search(pattern, content_lower):
            return "regulatory_constraint"
    for pattern in _PORTFOLIO_ACTION_PATTERNS:
        if re.search(pattern, content_lower):
            return "portfolio_action"
    for pattern in _MACRO_EVENT_PATTERNS:
        if re.search(pattern, content_lower):
            return "macro_event"

    for signal in EDUCATION_SIGNALS:
        if signal.lower() in content_lower:
            return "education_context"

    return None


def extract_memory_candidates(
    summary_text: str,
    conversation_id: str,
    user_id: Optional[str],
) -> List[PromotionCandidate]:
    """Split *summary_text* into sentences and return promotable candidates."""
    candidates = []
    for sentence in re.split(r"[.!?]+", summary_text):
        sentence = sentence.strip()
        if not sentence:
            continue
        category = classify_memory_category(sentence)
        if category:
            candidates.append(
                PromotionCandidate(
                    content=sentence,
                    category=category,
                    source_conversation=conversation_id,
                    source_type="summary",
                    confidence=0.8,
                    metadata={"user_id": user_id},
                    created_at=datetime.utcnow(),
                )
            )
    return candidates
