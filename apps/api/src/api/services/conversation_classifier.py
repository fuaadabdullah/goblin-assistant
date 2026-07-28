"""Keyword-based conversation category classifier."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from api.routing.keyword_matcher import keyword_matches_text


class ConversationCategory(str, Enum):
    CODING = "coding"
    TRADING = "trading"
    FINANCE = "finance"
    HEALTH = "health"
    RELATIONSHIPS = "relationships"
    RESEARCH = "research"


class ConversationClassifier:
    # trading before finance — more specific overlap terms
    _KEYWORDS: dict[ConversationCategory, list[str]] = {
        ConversationCategory.CODING: [
            "function",
            "code",
            "python",
            "javascript",
            "typescript",
            "bug",
            "compile",
            "git",
            "api",
            "database",
            "algorithm",
            "deploy",
            "debug",
            "class",
            "method",
            "loop",
            "syntax",
            "library",
            "framework",
            "npm",
            "pip",
            "docker",
            "bash",
            "terminal",
            "error",
            "exception",
            "test",
            "import",
            "variable",
            "refactor",
        ],
        ConversationCategory.TRADING: [
            "stock",
            "ticker",
            "buy",
            "sell",
            "portfolio",
            "dividend",
            "crypto",
            "bitcoin",
            "ethereum",
            "trade",
            "position",
            "options",
            "futures",
            "forex",
            "chart",
            "candlestick",
            "rsi",
            "moving average",
            "short",
            "long",
            "market cap",
            "price target",
            "breakout",
        ],
        ConversationCategory.FINANCE: [
            "budget",
            "savings",
            "debt",
            "loan",
            "mortgage",
            "expense",
            "tax",
            "investment",
            "interest",
            "financial",
            "credit",
            "insurance",
            "retire",
            "pension",
            "salary",
            "cash flow",
            "invoice",
            "accounting",
            "net worth",
            "income",
        ],
        ConversationCategory.HEALTH: [
            "doctor",
            "symptom",
            "medication",
            "exercise",
            "diet",
            "sleep",
            "pain",
            "treatment",
            "diagnosis",
            "prescription",
            "hospital",
            "mental health",
            "anxiety",
            "depression",
            "nutrition",
            "fitness",
            "wellness",
            "disease",
            "injury",
            "therapy",
            "calories",
            "workout",
            "headache",
            "nausea",
            "nauseous",
            "fever",
            "sick",
            "cough",
            "dizzy",
            "fatigue",
            "chronic",
            "blood pressure",
            "cholesterol",
            "vitamin",
            "supplement",
            "stress",
        ],
        ConversationCategory.RELATIONSHIPS: [
            "relationship",
            "partner",
            "boyfriend",
            "girlfriend",
            "husband",
            "wife",
            "marriage",
            "divorce",
            "dating",
            "family",
            "conflict",
            "communication",
            "love",
            "breakup",
            "trust",
            "boundaries",
            "attachment",
            "intimacy",
        ],
        ConversationCategory.RESEARCH: [
            "study",
            "paper",
            "research",
            "analysis",
            "methodology",
            "literature",
            "hypothesis",
            "evidence",
            "findings",
            "survey",
            "statistics",
            "experiment",
            "journal",
            "academic",
            "peer-reviewed",
            "citation",
            "conclusion",
            "data",
            "review",
            "current information",
            "current events",
            "current",
            "latest",
            "recent",
            "real time",
            "real-time",
            "up to date",
            "up-to-date",
            "what's new",
            "what is new",
            "breaking",
        ],
    }

    def classify(self, text: str, existing: Optional[str] = None) -> Optional[str]:
        """Return a category slug, or None if the message has no signal.

        Sticky: an established category (existing != None) requires ≥2 hits to change.
        """
        if not text:
            return existing

        lower = text.lower()
        scores: dict[ConversationCategory, int] = {}
        for cat, keywords in self._KEYWORDS.items():
            hits = sum(1 for kw in keywords if keyword_matches_text(lower, kw))
            if hits:
                scores[cat] = hits

        if not scores:
            return existing

        best_cat, best_score = max(scores.items(), key=lambda x: x[1])
        if best_score < 2 and existing:
            return existing
        return best_cat.value


conversation_classifier = ConversationClassifier()
