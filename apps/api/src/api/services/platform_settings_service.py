"""Route-safe service facade for account, settings, support, and privacy data."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.errors import DomainError
from api.storage.conversations import DatabaseConversationStore
from api.storage.database import get_db, get_readonly_db
from api.storage.models import ApiKeyModel, FeatureFlagModel, SupportTicketModel
from api.storage.saas_service import SaaSSettingsService
from api.storage.user_service import UserService

get_platform_db = get_db
get_readonly_platform_db = get_readonly_db


async def save_account_profile(
    *,
    db: AsyncSession,
    user_id: str,
    name: Optional[str],
    email: Optional[str],
    avatar_url: Optional[str],
) -> Dict[str, Any]:
    user_service = UserService(db)
    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise DomainError(
            code="ACCOUNT_USER_NOT_FOUND",
            message="User not found",
            status_code=404,
        )

    if name is not None:
        user.name = name
    if email is not None and email != user.email:
        existing = await user_service.get_user_by_email(email)
        if existing:
            raise DomainError(
                code="ACCOUNT_EMAIL_IN_USE",
                message="Email already in use",
                status_code=400,
            )
        user.email = email

    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "avatar_url": avatar_url,
    }


async def get_account_profile(db: AsyncSession, user_id: str) -> Optional[Dict[str, Any]]:
    return await SaaSSettingsService(db).get_account_profile(user_id)


async def save_account_preferences(
    db: AsyncSession,
    user_id: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    return await SaaSSettingsService(db).save_account_preferences(user_id, payload)


async def get_account_preferences(db: AsyncSession, user_id: str) -> Optional[Dict[str, Any]]:
    return await SaaSSettingsService(db).get_account_preferences(user_id)


async def get_chat_settings(db: AsyncSession, user_id: str) -> Optional[Dict[str, Any]]:
    return await SaaSSettingsService(db).get_chat_settings(user_id)


async def save_chat_settings(
    db: AsyncSession,
    user_id: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    return await SaaSSettingsService(db).save_chat_settings(user_id, payload)


async def lookup_user_id_by_email(db: AsyncSession, email: Optional[str]) -> Optional[str]:
    if not email:
        return None
    user = await UserService(db).get_user_by_email(email)
    return None if user is None else user.id


async def create_support_ticket_with_notification(
    *,
    db: AsyncSession,
    email: Optional[str],
    category: Optional[str],
    message: str,
    attachment_url: Optional[str],
) -> Any:
    service = SaaSSettingsService(db)
    support_user_id = await lookup_user_id_by_email(db, email)
    ticket = await service.create_support_ticket(
        {
            "user_id": support_user_id,
            "email": email,
            "category": category,
            "subject": (category or "support").replace("_", " ").title(),
            "message": message,
            "attachment_url": attachment_url,
            "triage": {},
            "metadata": {"source": "support_form"},
        }
    )
    if support_user_id:
        await service.create_notification(
            {
                "user_id": support_user_id,
                "title": "Support request received",
                "body": "We received your support request and will review it shortly.",
                "category": "support",
                "metadata": {
                    "source": "support_form",
                    "support_ticket_id": ticket.ticket_id,
                    "support_category": category,
                },
            }
        )
    return ticket


async def list_notifications(db: AsyncSession, user_id: str) -> List[Any]:
    return await SaaSSettingsService(db).list_notifications(user_id)


async def create_notification(db: AsyncSession, payload: Dict[str, Any]) -> Any:
    return await SaaSSettingsService(db).create_notification(payload)


async def mark_notification_read(db: AsyncSession, notification_id: str) -> Optional[Any]:
    return await SaaSSettingsService(db).mark_notification_read(notification_id)


async def resolve_feature_flag(
    db: AsyncSession,
    flag_key: str,
    *,
    user_id: Optional[str] = None,
    role: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    return await SaaSSettingsService(db).resolve_feature_flag(
        flag_key,
        user_id=user_id,
        role=role,
    )


async def upsert_feature_flag(db: AsyncSession, flag_key: str, payload: Dict[str, Any]) -> Any:
    return await SaaSSettingsService(db).upsert_feature_flag(flag_key, payload)


async def list_user_conversations(user_id: str, *, limit: int) -> List[Any]:
    return await DatabaseConversationStore().list_conversations(user_id=user_id, limit=limit)


async def delete_user_conversations(user_id: str, *, limit: int = 10000) -> int:
    conversation_store = DatabaseConversationStore()
    conversations = await conversation_store.list_conversations(user_id=user_id, limit=limit)
    for conversation in conversations:
        await conversation_store.delete_conversation(conversation.conversation_id)
    return len(conversations)


async def delete_platform_user_data(db: AsyncSession, user_id: str) -> Dict[str, int]:
    return await SaaSSettingsService(db).delete_user_data(user_id)


async def count_support_tickets(db: AsyncSession, user_id: str) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(SupportTicketModel)
        .where(SupportTicketModel.user_id == user_id)
    )
    return int(result.scalar_one() or 0)


async def count_api_keys(db: AsyncSession, user_id: str) -> int:
    result = await db.execute(
        select(func.count()).select_from(ApiKeyModel).where(ApiKeyModel.user_id == user_id)
    )
    return int(result.scalar_one() or 0)


async def count_feature_flags(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(FeatureFlagModel))
    return int(result.scalar_one() or 0)


async def count_notifications(db: AsyncSession, user_id: str) -> int:
    return len(await list_notifications(db, user_id))


async def update_rag_consent(user_id: str, consent_given: bool) -> None:
    from api.storage.preferences_service import preferences_service

    await preferences_service.update_rag_consent(user_id, consent_given)
