"""AI-powered error summarization for Sentry webhook alerts."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a senior on-call engineer. Given an error report (title, culprit, and stack trace),
produce a concise analysis and return ONLY a JSON object — no prose, no markdown fences.

JSON schema:
{
  "root_cause": "one sentence: what went wrong and where",
  "user_impact": "what the end-user experienced (e.g. 'chat messages failed to send')",
  "likely_fix": "where to look or what to change — file:line if visible in the trace",
  "one_liner": "≤80 char summary for a Slack notification subject"
}

Be specific. Reference file paths and line numbers from the trace when available.\
"""


@dataclass
class ErrorSummary:
    root_cause: str
    user_impact: str
    likely_fix: str
    one_liner: str

    @classmethod
    def from_title(cls, title: str) -> "ErrorSummary":
        """Fallback when LLM is unavailable."""
        short = title[:77] + "..." if len(title) > 80 else title
        return cls(
            root_cause=title,
            user_impact="Unknown — check Sentry for details",
            likely_fix="Review the stack trace in Sentry",
            one_liner=short,
        )


def _parse_summary_json(text: str) -> ErrorSummary:
    clean = re.sub(r"^```[a-z]*\s*", "", text.strip(), flags=re.MULTILINE)
    clean = re.sub(r"```\s*$", "", clean, flags=re.MULTILINE).strip()
    data = json.loads(clean)
    return ErrorSummary(
        root_cause=data.get("root_cause", ""),
        user_impact=data.get("user_impact", ""),
        likely_fix=data.get("likely_fix", ""),
        one_liner=data.get("one_liner", ""),
    )


def _format_frames(frames: List[Dict[str, Any]]) -> str:
    """Format Sentry stack frames into a readable trace string (top 15)."""
    lines = []
    for frame in frames[-15:]:
        filename = frame.get("filename") or frame.get("module", "?")
        lineno = frame.get("lineno", "?")
        func = frame.get("function", "?")
        ctx = frame.get("context_line", "").strip()
        line = f"  {filename}:{lineno} in {func}"
        if ctx:
            line += f"\n    {ctx}"
        lines.append(line)
    return "\n".join(lines) if lines else "(no frames)"


async def summarize_error(
    title: str,
    culprit: str,
    stack_trace: str,
    level: str = "error",
) -> ErrorSummary:
    """Call the LLM to produce a plain-English error summary.

    Falls back to a stub summary if the provider call fails.
    """
    from api.providers.dispatcher import invoke_provider

    prompt = (
        f"Error level: {level}\nTitle: {title}\nCulprit: {culprit}\n\nStack trace:\n{stack_trace}"
    )

    try:
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "model": "claude-haiku-4-5",
            "max_tokens": 400,
            "temperature": 0.1,
            "system": _SYSTEM_PROMPT,
        }
        response = await invoke_provider(
            pid=None,
            model="claude-haiku-4-5",
            payload=payload,
            timeout_ms=15_000,
            stream=False,
        )
        if isinstance(response, dict) and response.get("ok"):
            return _parse_summary_json(response["result"]["text"])
    except Exception as exc:
        logger.warning("Error summarizer LLM call failed: %s", exc)

    return ErrorSummary.from_title(title)
