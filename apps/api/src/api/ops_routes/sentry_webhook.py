"""Sentry issue-alert webhook receiver.

Sentry POSTs here when a new issue is created or regresses.
We summarize via AI and forward to Slack.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from api.services.error_summarizer import _format_frames, summarize_error

logger = logging.getLogger(__name__)

router = APIRouter()

_LEVEL_EMOJI = {
    "fatal": "💀",
    "error": "🔥",
    "warning": "⚠️",
    "info": "ℹ️",
}


def _extract_stack_trace(event: Dict[str, Any]) -> str:
    try:
        exception = event.get("exception", {})
        values = exception.get("values", [])
        if not values:
            return "(no stack trace)"
        exc_value = values[-1]
        frames = exc_value.get("stacktrace", {}).get("frames", [])
        return _format_frames(frames)
    except Exception:
        return "(could not extract stack trace)"


def _build_slack_blocks(
    level: str,
    one_liner: str,
    root_cause: str,
    user_impact: str,
    likely_fix: str,
    sentry_url: str,
    culprit: str,
) -> Dict[str, Any]:
    emoji = _LEVEL_EMOJI.get(level.lower(), "🔥")
    return {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} {level.upper()} — {one_liner}",
                    "emoji": True,
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Root cause*\n{root_cause}"},
                    {"type": "mrkdwn", "text": f"*User impact*\n{user_impact}"},
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Likely fix*\n{likely_fix}"},
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Culprit: `{culprit}` | <{sentry_url}|View in Sentry →>",
                    }
                ],
            },
        ]
    }


async def _post_to_slack(payload: Dict[str, Any]) -> None:
    url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not url:
        logger.info("SLACK_WEBHOOK_URL not set — skipping Slack notification")
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
    except Exception as exc:
        logger.error("Failed to post Sentry alert to Slack: %s", exc)


@router.post("/sentry-webhook")
async def sentry_webhook(request: Request) -> JSONResponse:
    """Receive a Sentry issue alert, summarize it with AI, and post to Slack."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid JSON"}, status_code=400)

    # Sentry alert webhook payload shape
    data = body.get("data", {})
    issue = data.get("issue", {})
    event = data.get("event", {})

    title = issue.get("title") or event.get("title") or "Unknown error"
    culprit = issue.get("culprit") or event.get("culprit") or "unknown"
    level = issue.get("level") or event.get("level") or "error"
    sentry_url = issue.get("web_url") or issue.get("permalink") or ""

    stack_trace = _extract_stack_trace(event)

    summary = await summarize_error(
        title=title,
        culprit=culprit,
        stack_trace=stack_trace,
        level=level,
    )

    slack_payload = _build_slack_blocks(
        level=level,
        one_liner=summary.one_liner,
        root_cause=summary.root_cause,
        user_impact=summary.user_impact,
        likely_fix=summary.likely_fix,
        sentry_url=sentry_url,
        culprit=culprit,
    )

    await _post_to_slack(slack_payload)

    logger.info("Sentry webhook processed — %s [%s] %s", title, level, summary.one_liner)
    return JSONResponse({"ok": True})
