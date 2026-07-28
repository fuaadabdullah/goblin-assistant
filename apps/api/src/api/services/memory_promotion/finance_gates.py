import re
from typing import Any, Dict, List

from .models import PromotionCandidate, PromotionGate

FINANCE_CATEGORIES = {
    "instrument",
    "risk_signal",
    "regulatory_constraint",
    "portfolio_action",
    "macro_event",
}


def evaluate_finance_gates(candidate: PromotionCandidate) -> Dict[str, Any]:
    """Run finance-specific promotion gates (additive, non-blocking)."""
    passed: List[PromotionGate] = []
    failed: List[PromotionGate] = []
    reasons: List[str] = []
    content_lower = candidate.content.lower()

    if candidate.category == "instrument":
        if entity_looks_plausible(content_lower):
            passed.append(PromotionGate.ENTITY_PLAUSIBILITY)
        else:
            failed.append(PromotionGate.ENTITY_PLAUSIBILITY)
            reasons.append("Financial entity failed plausibility check")

    if candidate.category == "risk_signal":
        if re.search(r"\d", content_lower) or re.search(
            r"(increased|decreased|above|below|higher|lower)", content_lower
        ):
            passed.append(PromotionGate.RISK_CONTEXT)
        else:
            failed.append(PromotionGate.RISK_CONTEXT)
            reasons.append("Risk signal lacks numeric or comparative context")

    sensitive_patterns = [
        r"\b(insider\s*trading|material\s*non.public|mnpi)\b",
        r"\b(ssn|social\s*security|account\s*number)\b",
    ]
    if any(re.search(p, content_lower) for p in sensitive_patterns):
        failed.append(PromotionGate.COMPLIANCE_MARKER)
        reasons.append("Content contains sensitive compliance markers — review required")
    else:
        passed.append(PromotionGate.COMPLIANCE_MARKER)

    return {"passed": passed, "failed": failed, "reasons": reasons}


def entity_looks_plausible(content: str) -> bool:
    """Return True if content mentions a recognisable instrument keyword."""
    anchors = [
        r"\b(stock|share|bond|etf|fund|option|futures|commodity|equity|index)\b",
        r"\b(s&p|nasdaq|dow|russell|msci|ftse|treasury)\b",
        r"\b(price|dividend|market\s*cap|earnings|yield)\b",
    ]
    return any(re.search(p, content) for p in anchors)
