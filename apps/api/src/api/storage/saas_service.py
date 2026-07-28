"""Persistence helpers for account, settings, support, and platform domains."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from .crypto import decrypt_secret, encrypt_secret
from .models import (
    ApiKeyModel,
    ChatSettingsModel,
    FeatureFlagModel,
    GlobalSettingModel,
    NotificationModel,
    ProviderSettingsModel,
    SupportTicketModel,
    UserModel,
    UserPreferencesModel,
)


class SaaSSettingsService:
    """Domain-friendly persistence service for Phase 6 settings."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user(self, user_id: str) -> Optional[UserModel]:
        result = await self.session.execute(select(UserModel).where(UserModel.id == user_id))
        return result.scalar_one_or_none()

    async def get_account_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        user = await self.get_user(user_id)
        if not user:
            return None
        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar_url": None,
        }

    async def save_account_profile(
        self, user_id: str, *, name: Optional[str], email: Optional[str]
    ) -> Dict[str, Any]:
        user = await self.get_user(user_id)
        if not user:
            raise LookupError("user-not-found")
        if name is not None:
            user.name = name
        if email is not None:
            user.email = email
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar_url": None,
        }

    async def get_account_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        result = await self.session.execute(
            select(UserPreferencesModel).where(UserPreferencesModel.user_id == user_id)
        )
        prefs = result.scalar_one_or_none()
        if not prefs:
            return None
        ui = prefs.ui_preferences or {}
        return {
            "theme": ui.get("theme"),
            "default_model": prefs.default_model,
            "default_provider": prefs.default_provider,
            "notifications_enabled": ui.get("notifications", True),
            "language": ui.get("language"),
            "summaries": ui.get("summaries", True),
            "familyMode": ui.get("familyMode", False),
            "other": prefs.privacy_settings or {},
        }

    async def save_account_preferences(
        self, user_id: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        result = await self.session.execute(
            select(UserPreferencesModel).where(UserPreferencesModel.user_id == user_id)
        )
        prefs = result.scalar_one_or_none()
        if prefs is None:
            prefs = UserPreferencesModel(user_id=user_id)
            self.session.add(prefs)

        prefs.default_provider = payload.get("default_provider", prefs.default_provider)
        prefs.default_model = payload.get("default_model", prefs.default_model)
        prefs.rag_consent = (
            "true" if payload.get("rag_consent", prefs.rag_consent == "true") else "false"
        )
        prefs.ui_preferences = {
            **(prefs.ui_preferences or {}),
            "theme": payload.get("theme"),
            "notifications": payload.get("notifications_enabled"),
            "language": payload.get("language"),
            "summaries": payload.get("summaries"),
            "familyMode": payload.get("familyMode"),
        }
        prefs.privacy_settings = payload.get("other", prefs.privacy_settings or {})
        prefs.version = (prefs.version or 1) + 1
        prefs.updated_at = datetime.utcnow()
        await self.session.flush()
        await self.session.refresh(prefs)
        return await self.get_account_preferences(user_id) or {}

    async def get_chat_settings(self, user_id: str) -> Optional[Dict[str, Any]]:
        result = await self.session.execute(
            select(ChatSettingsModel).where(ChatSettingsModel.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        return {
            "user_id": row.user_id,
            "default_provider": row.default_provider,
            "default_model": row.default_model,
            "system_prompt": row.system_prompt,
            "temperature": row.temperature,
            "max_tokens": row.max_tokens,
            "summary_enabled": row.summary_enabled,
            "metadata": row.metadata_ or {},
        }

    async def save_chat_settings(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        result = await self.session.execute(
            select(ChatSettingsModel).where(ChatSettingsModel.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = ChatSettingsModel(user_id=user_id)
            self.session.add(row)
        for key in (
            "default_provider",
            "default_model",
            "system_prompt",
            "temperature",
            "max_tokens",
            "summary_enabled",
        ):
            if key in payload:
                setattr(row, key, payload.get(key))
        row.metadata_ = payload.get("metadata", row.metadata_ or {})
        row.version = (row.version or 1) + 1
        row.updated_at = datetime.utcnow()
        await self.session.flush()
        await self.session.refresh(row)
        return await self.get_chat_settings(user_id) or {}

    async def list_provider_settings(self) -> List[ProviderSettingsModel]:
        result = await self.session.execute(select(ProviderSettingsModel))
        return list(result.scalars().all())

    async def upsert_provider_settings(
        self, provider_name: str, payload: Dict[str, Any]
    ) -> ProviderSettingsModel:
        result = await self.session.execute(
            select(ProviderSettingsModel).where(
                ProviderSettingsModel.provider_name == provider_name
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = ProviderSettingsModel(provider_name=provider_name)
            self.session.add(row)
        row.endpoint = payload.get("endpoint", row.endpoint)
        row.enabled = payload.get("enabled", row.enabled if row.enabled is not None else True)
        row.priority = payload.get("priority", row.priority or 0)
        row.weight = payload.get("weight", row.weight or 1.0)
        row.base_url = payload.get("base_url", row.base_url)
        if "models" in payload:
            row.models = payload.get("models") or []
        if payload.get("api_key"):
            row.api_key_encrypted = encrypt_secret(str(payload["api_key"]))
        row.metadata_ = payload.get("metadata", row.metadata_ or {})
        row.version = (row.version or 1) + 1
        row.updated_at = datetime.utcnow()
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def get_provider_api_key(self, provider_name: str) -> Optional[str]:
        result = await self.session.execute(
            select(ProviderSettingsModel).where(
                ProviderSettingsModel.provider_name == provider_name
            )
        )
        row = result.scalar_one_or_none()
        if not row or not row.api_key_encrypted:
            return None
        return decrypt_secret(row.api_key_encrypted)

    async def set_global_setting(self, key: str, value: Any) -> Dict[str, Any]:
        result = await self.session.execute(
            select(GlobalSettingModel).where(GlobalSettingModel.key == key)
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = GlobalSettingModel(key=key)
            self.session.add(row)
        row.value = (
            value if isinstance(value, (dict, list, str, int, float, bool)) else {"value": value}
        )
        row.updated_at = datetime.utcnow()
        await self.session.flush()
        await self.session.refresh(row)
        return {"key": row.key, "value": row.value}

    async def get_global_setting(self, key: str) -> Optional[Any]:
        result = await self.session.execute(
            select(GlobalSettingModel).where(GlobalSettingModel.key == key)
        )
        row = result.scalar_one_or_none()
        return None if row is None else row.value

    async def create_support_ticket(self, payload: Dict[str, Any]) -> SupportTicketModel:
        ticket = SupportTicketModel(
            user_id=payload.get("user_id"),
            email=payload.get("email"),
            category=payload.get("category"),
            priority=payload.get("priority"),
            status=payload.get("status", "received"),
            subject=payload.get("subject"),
            message=payload["message"],
            attachment_url=payload.get("attachment_url"),
            triage=payload.get("triage", {}),
            metadata_=payload.get("metadata", {}),
        )
        self.session.add(ticket)
        await self.session.flush()
        await self.session.refresh(ticket)
        return ticket

    async def create_notification(self, payload: Dict[str, Any]) -> NotificationModel:
        notification = NotificationModel(
            user_id=payload["user_id"],
            channel=payload.get("channel", "in_app"),
            title=payload["title"],
            body=payload["body"],
            category=payload.get("category"),
            metadata_=payload.get("metadata", {}),
        )
        self.session.add(notification)
        await self.session.flush()
        await self.session.refresh(notification)
        return notification

    async def list_notifications(self, user_id: str) -> List[NotificationModel]:
        result = await self.session.execute(
            select(NotificationModel)
            .where(NotificationModel.user_id == user_id)
            .order_by(NotificationModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def mark_notification_read(self, notification_id: str) -> Optional[NotificationModel]:
        result = await self.session.execute(
            select(NotificationModel).where(NotificationModel.notification_id == notification_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.is_read = True
        row.read_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def upsert_feature_flag(self, key: str, payload: Dict[str, Any]) -> FeatureFlagModel:
        result = await self.session.execute(
            select(FeatureFlagModel).where(FeatureFlagModel.flag_key == key)
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = FeatureFlagModel(flag_key=key)
            self.session.add(row)
        for field in (
            "enabled",
            "default_value",
            "user_overrides",
            "rollout_percent",
            "target_users",
            "target_roles",
        ):
            if field in payload:
                setattr(row, field, payload.get(field))
        row.metadata_ = payload.get("metadata", row.metadata_ or {})
        row.version = (row.version or 1) + 1
        row.updated_at = datetime.utcnow()
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def resolve_feature_flag(
        self, key: str, *, user_id: Optional[str] = None, role: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        result = await self.session.execute(
            select(FeatureFlagModel).where(FeatureFlagModel.flag_key == key)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        enabled = bool(row.enabled)
        override = row.user_overrides or {}
        if user_id and user_id in override:
            enabled = bool(override[user_id])
        if not enabled and role and role in (row.target_roles or []):
            enabled = True
        return {
            "flag_key": row.flag_key,
            "enabled": enabled,
            "default_value": row.default_value,
            "rollout_percent": row.rollout_percent,
            "target_users": row.target_users or [],
            "target_roles": row.target_roles or [],
        }

    async def delete_user_data(self, user_id: str) -> Dict[str, int]:
        counts = {
            "preferences": 0,
            "chat_settings": 0,
            "api_keys": 0,
            "notifications": 0,
            "support_tickets": 0,
        }
        counts["preferences"] = (
            await self.session.execute(
                delete(UserPreferencesModel).where(UserPreferencesModel.user_id == user_id)
            )
        ).rowcount or 0
        counts["chat_settings"] = (
            await self.session.execute(
                delete(ChatSettingsModel).where(ChatSettingsModel.user_id == user_id)
            )
        ).rowcount or 0
        counts["api_keys"] = (
            await self.session.execute(delete(ApiKeyModel).where(ApiKeyModel.user_id == user_id))
        ).rowcount or 0
        counts["notifications"] = (
            await self.session.execute(
                delete(NotificationModel).where(NotificationModel.user_id == user_id)
            )
        ).rowcount or 0
        counts["support_tickets"] = (
            await self.session.execute(
                delete(SupportTicketModel).where(SupportTicketModel.user_id == user_id)
            )
        ).rowcount or 0
        return counts
