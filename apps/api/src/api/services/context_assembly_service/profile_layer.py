"""User Profile layer assembler.

Provides a structured summary of user's goals, projects, and preferences.
Inserted early in the context (after system, before long-term memory) to ground the model
in who the user is before diving into conversation specifics.
"""

from typing import Any, Dict, Optional

import structlog

from ...services.user_profile_service import UserProfileService
from ...storage.database import get_readonly_db_context
from ...utils.tokenizer import count_tokens, trim_to_tokens
from .models import ContextBudget, ContextLayer

logger = structlog.get_logger()


async def get_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve and format user profile for context."""
    try:
        async with get_readonly_db_context() as session:
            profile_service = UserProfileService()
            profile = await profile_service.get_profile(user_id, session)

            if not profile:
                return None

            return {
                "goals": profile.goals,
                "projects": profile.projects,
                "preferences": profile.preferences,
                "key_entities": profile.key_entities,
            }
    except Exception as e:
        logger.error("Failed to retrieve user profile", error=str(e))
        return None


def format_user_profile(profile_data: Dict[str, Any]) -> str:
    """Format user profile as structured text."""
    if not profile_data:
        return ""

    lines = ["## User Profile"]

    # Goals
    goals = profile_data.get("goals") or []
    if goals:
        lines.append(f"Goals: {', '.join(goals)}")

    # Projects
    projects = profile_data.get("projects") or []
    if projects:
        lines.append(f"Active projects: {', '.join(projects)}")

    # Preferences
    preferences = profile_data.get("preferences") or {}
    if preferences:
        for key, value in list(preferences.items())[:5]:
            lines.append(f"Preference - {key}: {value}")

    # Key entities
    key_entities = profile_data.get("key_entities") or {}
    for entity_type, entities in list(key_entities.items())[:3]:
        if entities:
            values = [e.get("value") for e in entities[:5] if e.get("value")]
            if values:
                lines.append(f"{entity_type.title()}: {', '.join(values)}")

    return "\n".join(lines) if len(lines) > 1 else ""


async def assemble_profile_layer(
    user_id: str,
    remaining_tokens: int,
    budget: ContextBudget,
) -> Optional[ContextLayer]:
    """Assemble User Profile layer.

    Provides a structured summary of who the user is, grounding the model
    in user context before processing conversation specifics.
    """
    if remaining_tokens < budget.profile_tokens:
        return None

    try:
        profile_data = await get_user_profile(user_id)
        if not profile_data or not any(
            [
                profile_data.get("goals"),
                profile_data.get("projects"),
                profile_data.get("preferences"),
            ]
        ):
            return None

        profile_content = format_user_profile(profile_data)
        if not profile_content:
            return None

        tokens = count_tokens(profile_content)

        if tokens > budget.profile_tokens:
            profile_content = trim_to_tokens(profile_content, budget.profile_tokens)
            tokens = budget.profile_tokens

        return ContextLayer(
            name="user_profile",
            content=profile_content,
            tokens=tokens,
            source_count=len(profile_data.get("goals", [])) + len(profile_data.get("projects", [])),
            metadata={
                "type": "profile",
                "goals": len(profile_data.get("goals", [])),
                "projects": len(profile_data.get("projects", [])),
                "description": "Structured user profile (goals, projects, preferences, key entities)",
            },
        )
    except Exception as e:
        logger.error("Failed to assemble user profile layer", error=str(e))
        return None
