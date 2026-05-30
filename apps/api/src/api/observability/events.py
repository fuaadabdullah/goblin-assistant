"""Typed domain-event persistence and retrieval."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, cast
import uuid

import structlog
from pydantic import BaseModel
from sqlalchemy import desc, select

from api.core.contracts import EventEnvelope, EventType, JsonObject

logger = structlog.get_logger()


def _json_payload(payload: BaseModel | JsonObject) -> JsonObject:
    if isinstance(payload, BaseModel):
        return cast(JsonObject, payload.model_dump(mode="json", exclude_none=True))
    return payload


def _event_from_model(row: Any) -> EventEnvelope[JsonObject]:
    return EventEnvelope[JsonObject](
        event_id=str(row.event_id),
        event_type=cast(EventType, row.event_type),
        occurred_at=row.occurred_at.isoformat(),
        source=str(row.source),
        actor_user_id=row.actor_user_id,
        correlation_id=row.correlation_id,
        payload=cast(JsonObject, row.payload or {}),
    )


class DomainEventEmitter:
    """Persist domain events without making business flows depend on observability."""

    async def emit(
        self,
        event_type: EventType,
        source: str,
        payload: BaseModel | JsonObject,
        *,
        actor_user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        occurred_at: Optional[datetime] = None,
    ) -> Optional[EventEnvelope[JsonObject]]:
        try:
            return await self._persist(
                event_type=event_type,
                source=source,
                payload=_json_payload(payload),
                actor_user_id=actor_user_id,
                correlation_id=correlation_id,
                occurred_at=occurred_at or datetime.utcnow(),
            )
        except Exception as exc:
            logger.warning(
                "domain_event_emit_failed",
                event_type=event_type,
                source=source,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            return None

    async def _persist(
        self,
        *,
        event_type: EventType,
        source: str,
        payload: JsonObject,
        actor_user_id: Optional[str],
        correlation_id: Optional[str],
        occurred_at: datetime,
    ) -> EventEnvelope[JsonObject]:
        from api.storage.database import get_db_context
        from api.storage.models import DomainEventModel

        event_id = str(uuid.uuid4())
        async with get_db_context() as session:
            row = DomainEventModel(
                event_id=event_id,
                event_type=event_type,
                occurred_at=occurred_at,
                source=source,
                actor_user_id=actor_user_id,
                correlation_id=correlation_id,
                payload=payload,
            )
            session.add(row)

        return EventEnvelope[JsonObject](
            event_id=event_id,
            event_type=event_type,
            occurred_at=occurred_at.isoformat(),
            source=source,
            actor_user_id=actor_user_id,
            correlation_id=correlation_id,
            payload=payload,
        )

    async def get_event(self, event_id: str) -> Optional[EventEnvelope[JsonObject]]:
        from api.storage.database import get_db_context
        from api.storage.models import DomainEventModel

        async with get_db_context() as session:
            result = await session.execute(
                select(DomainEventModel).where(DomainEventModel.event_id == event_id)
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return _event_from_model(row)

    async def list_events(
        self,
        *,
        event_type: Optional[EventType] = None,
        actor_user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 100,
    ) -> list[EventEnvelope[JsonObject]]:
        from api.storage.database import get_db_context
        from api.storage.models import DomainEventModel

        query = select(DomainEventModel).order_by(desc(DomainEventModel.occurred_at)).limit(limit)
        if event_type is not None:
            query = query.where(DomainEventModel.event_type == event_type)
        if actor_user_id is not None:
            query = query.where(DomainEventModel.actor_user_id == actor_user_id)
        if correlation_id is not None:
            query = query.where(DomainEventModel.correlation_id == correlation_id)
        if source is not None:
            query = query.where(DomainEventModel.source == source)

        async with get_db_context() as session:
            result = await session.execute(query)
            return [_event_from_model(row) for row in result.scalars().all()]


event_emitter = DomainEventEmitter()
