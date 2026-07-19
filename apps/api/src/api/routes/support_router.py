"""
Support message endpoint
Handles user support/feedback submissions and AI-powered issue triage.
"""

import json
import logging
import os
import re
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.contracts import SuccessEnvelope
from api.core.errors import DomainError
from api.storage.database import get_db
from api.storage.saas_service import SaaSSettingsService
from api.storage.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/support", tags=["support"])


class SupportMessage(BaseModel):
    message: str
    email: Optional[str] = None
    category: Optional[str] = None
    attachment_url: Optional[str] = None


class SupportResponse(BaseModel):
    id: str
    status: str
    timestamp: str


async def _lookup_support_user_id(db: AsyncSession, email: Optional[str]) -> Optional[str]:
    if not email:
        return None

    user = await UserService(db).get_user_by_email(email)
    return None if user is None else str(user.id)


async def _attach_support_recipient(
    db: AsyncSession,
    ticket_id: str,
    user_id: Optional[str],
    category: Optional[str],
) -> None:
    """Queue a confirmation notification for a known support recipient."""
    try:
        if not user_id:
            return

        settings = SaaSSettingsService(db)
        await settings.create_notification(
            {
                "user_id": user_id,
                "title": "Support request received",
                "body": "We received your support request and will review it shortly.",
                "category": "support",
                "metadata": {
                    "source": "support_form",
                    "support_ticket_id": ticket_id,
                    "support_category": category,
                },
            }
        )
    except Exception as exc:  # pragma: no cover - best-effort notification path
        logger.warning(
            "support notification side effect failed for ticket %s user %s: %s",
            ticket_id,
            user_id,
            exc,
        )


@router.post("/message", response_model=SuccessEnvelope[SupportResponse])
async def send_support_message(
    request: SupportMessage,
    db: AsyncSession = Depends(get_db),
) -> SuccessEnvelope[SupportResponse]:
    """Submit a support message"""
    try:
        if not request.message or len(request.message.strip()) < 1:
            raise DomainError(
                code="SUPPORT_MESSAGE_REQUIRED",
                message="Message is required",
                status_code=400,
            )

        service = SaaSSettingsService(db)
        support_user_id = await _lookup_support_user_id(db, request.email)
        ticket = await service.create_support_ticket(
            {
                "user_id": support_user_id,
                "email": request.email,
                "category": request.category,
                "subject": (request.category or "support").replace("_", " ").title(),
                "message": request.message.strip(),
                "attachment_url": request.attachment_url,
                "triage": {},
                "metadata": {"source": "support_form"},
            }
        )
        await _attach_support_recipient(
            db, str(ticket.ticket_id), support_user_id, request.category
        )

        return SuccessEnvelope(
            data=SupportResponse(
                id=str(ticket.ticket_id),
                status=str(ticket.status),
                timestamp=ticket.created_at.isoformat(),
            )
        )
    except DomainError:
        raise
    except Exception as e:
        raise DomainError(
            code="SUPPORT_SUBMIT_FAILED",
            message="Failed to submit support message",
            status_code=500,
            details={"reason": str(e)},
        ) from e


# ---------------------------------------------------------------------------
# Triage
# ---------------------------------------------------------------------------

_TRIAGE_SYSTEM = """\
You are an issue triage assistant. Given a raw bug report (which may be extremely vague), extract
structured metadata and return ONLY a JSON object — no prose, no markdown fences.

JSON schema:
{
  "title": "<concise issue title, ≤72 characters>",
  "category": "<one of: bug | performance | ui | auth | data | integration | unknown>",
  "priority": "<one of: P0 | P1 | P2 | P3>",
  "affected_service": "<one of: chat | auth | api | search | sandbox | frontend | unknown>",
  "stack_trace": "<verbatim stack trace if present in the text, else null>",
  "cleaned_description": "<what the user almost certainly means, in one or two plain sentences>"
}

Priority guide:
- P0: data loss, complete auth failure, full outage
- P1: major feature broken, most users affected
- P2: degraded experience, workaround exists
- P3: minor annoyance or cosmetic issue

When unsure, default category to "bug" and priority to "P2".\
"""


def _build_triage_prompt(description: str, context: Optional[str]) -> str:
    parts = [f'Bug report: """{description}"""']
    if context:
        parts.append(f"Additional context: {context}")
    return "\n".join(parts)


def _parse_triage_json(text: str) -> Dict[str, Any]:
    """Extract JSON from LLM output, handling markdown fences."""
    # Strip potential ```json ... ``` wrapping
    clean = re.sub(r"^```[a-z]*\s*", "", text.strip(), flags=re.MULTILINE)
    clean = re.sub(r"```\s*$", "", clean, flags=re.MULTILINE).strip()
    return json.loads(clean)


def _fallback_triage(description: str) -> Dict[str, Any]:
    return {
        "title": description[:72] if len(description) <= 72 else description[:69] + "...",
        "category": "unknown",
        "priority": "P2",
        "affected_service": "unknown",
        "stack_trace": None,
        "cleaned_description": description,
    }


def _format_issue_body(description: str, triage: Dict[str, Any]) -> str:
    stack = triage.get("stack_trace") or "None extracted"
    return (
        "## User Report\n"
        f"> {description}\n\n"
        "## AI Triage\n"
        "| | |\n"
        "|---|---|\n"
        f"| Category | {triage['category']} |\n"
        f"| Priority | {triage['priority']} |\n"
        f"| Affected service | {triage['affected_service']} |\n\n"
        "## Cleaned Description\n"
        f"{triage['cleaned_description']}\n\n"
        "## Stack Trace\n"
        f"```\n{stack}\n```\n\n"
        "*Triaged automatically by Goblin Issue Triage*"
    )


class TriageRequest(BaseModel):
    description: str
    context: Optional[str] = None


class TriageResult(BaseModel):
    title: str
    category: str
    priority: str
    affected_service: str
    stack_trace: Optional[str] = None
    cleaned_description: str


class TriageResponse(BaseModel):
    id: str
    triage: TriageResult
    issue_url: Optional[str] = None
    issue_number: Optional[int] = None


@router.post("/triage", response_model=SuccessEnvelope[TriageResponse])
async def triage_issue(request: TriageRequest) -> SuccessEnvelope[TriageResponse]:
    """AI-powered bug report triage: categorise, prioritise, and optionally file a GitHub issue."""
    from api.assistant_tools.skills.github_tool_pkg.handlers import handle_github_create_issue
    from api.providers.dispatcher import invoke_provider

    if not request.description or not request.description.strip():
        raise DomainError(
            code="TRIAGE_DESCRIPTION_REQUIRED",
            message="A description is required",
            status_code=400,
        )

    triage_id = str(uuid.uuid4())
    raw = request.description.strip()

    # --- LLM extraction ---
    triage_data: Dict[str, Any]
    try:
        payload = {
            "messages": [{"role": "user", "content": _build_triage_prompt(raw, request.context)}],
            "model": "claude-haiku-4-5",
            "max_tokens": 512,
            "temperature": 0.1,
            "system": _TRIAGE_SYSTEM,
        }
        response = await invoke_provider(
            pid=None,
            model="claude-haiku-4-5",
            payload=payload,
            timeout_ms=20_000,
            stream=False,
        )
        if isinstance(response, dict) and response.get("ok"):
            triage_data = _parse_triage_json(response["result"]["text"])
        else:
            logger.warning("Triage LLM call returned non-ok response; using fallback")
            triage_data = _fallback_triage(raw)
    except Exception as e:
        logger.exception("Triage LLM call failed: %s", e)
        triage_data = _fallback_triage(raw)

    # --- GitHub issue ---
    issue_url: Optional[str] = None
    issue_number: Optional[int] = None
    gh_token = os.environ.get("GH_TOKEN", "").strip() or os.environ.get("GITHUB_TOKEN", "").strip()
    gh_owner = os.environ.get("GITHUB_REPO_OWNER", "")
    gh_repo = os.environ.get("GITHUB_REPO_NAME", "")

    if gh_token and gh_owner and gh_repo:
        try:
            labels = [triage_data["category"], triage_data["priority"]]
            result = await handle_github_create_issue(
                owner=gh_owner,
                repo=gh_repo,
                title=triage_data["title"],
                body=_format_issue_body(raw, triage_data),
                labels=labels,
            )
            if "error" not in result:
                issue_url = result.get("url")
                issue_number = result.get("number")
            else:
                logger.warning("GitHub issue creation failed: %s", result["error"])
        except Exception as e:
            logger.exception("GitHub issue creation raised: %s", e)

    return SuccessEnvelope(
        data=TriageResponse(
            id=triage_id,
            triage=TriageResult(
                **{
                    "title": triage_data.get("title", raw[:72]),
                    "category": triage_data.get("category", "unknown"),
                    "priority": triage_data.get("priority", "P2"),
                    "affected_service": triage_data.get("affected_service", "unknown"),
                    "stack_trace": triage_data.get("stack_trace"),
                    "cleaned_description": triage_data.get("cleaned_description", raw),
                }
            ),
            issue_url=issue_url,
            issue_number=issue_number,
        )
    )
