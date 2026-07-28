import re


def evaluate_content_quality(content: str) -> float:
    """
    Score content quality (0.0–1.0, higher is better).

    Penalises emotional language, temporal indicators, subjective statements,
    conditionals, questions, exclamations, and very short text.
    """
    content_lower = content.lower().strip()

    emotional_patterns = [
        r"\b(feeling|frustrated|stressed|excited|angry|happy|sad|tired)\b",
        r"\b(right now|today|this week|currently)\b",
        r"\b(i think|i believe|i feel)\b",
        r"\b(should|must|have to|need to)\b",
        r"\b(lol|lolz|lmao|rofl|=|>#)\b",
        r"\b(joke|funny|hilarious|silly)\b",
        r"\b(complain|complaining|annoyed|pissed|mad)\b",
        r"\b(if|when|maybe|perhaps|possibly)\b",
        r"\b(would|could|should|might)\b",
    ]

    penalty = 0.0
    for pattern in emotional_patterns:
        if re.search(pattern, content_lower):
            penalty += 0.2

    if len(content) < 20:
        penalty += 0.3
    if content.endswith("?"):
        penalty += 0.2
    if "!" in content:
        penalty += 0.1

    return 1.0 - min(penalty, 1.0)


def evaluate_stability(content: str) -> float:
    """
    Score how stable/declarative the content is (0.0–1.0, higher is better).

    Awards points for declarative and objective language; deducts for volatile
    or emotional phrasing.
    """
    content_lower = content.lower().strip()

    declarative_patterns = [
        r"\b(i am|i have|i work|i use|i prefer|i need)\b",
        r"\b(always|never|consistently|regularly)\b",
        r"\b(prefer|like|use|work|build|develop)\b",
    ]
    objective_patterns = [
        r"\b(project|system|tool|framework|language|technology)\b",
        r"\b(requirement|constraint|objective|goal)\b",
        r"\b(prefer|choice|option|alternative)\b",
    ]
    volatile_patterns = [
        r"\b(stressed|frustrated|excited|angry|today|right now)\b",
        r"\b(should|must|have to)\b",
        r"\b(complain|annoyed|mad)\b",
    ]

    score = 0.0
    for pattern in declarative_patterns:
        if re.search(pattern, content_lower):
            score += 0.2
    for pattern in objective_patterns:
        if re.search(pattern, content_lower):
            score += 0.1
    for pattern in volatile_patterns:
        if re.search(pattern, content_lower):
            score -= 0.3

    return max(0.0, min(1.0, score))
