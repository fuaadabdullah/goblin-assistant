"""Read-side service boundary for Goblin runtime catalog, history, and stats."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Protocol

from pydantic import ValidationError

from api.api_models import (
    GoblinHistoryEntry,
    GoblinHistoryResponse,
    GoblinListResponse,
    GoblinStatsCounters,
    GoblinStatsLatency,
    GoblinStatsResponse,
    GoblinStatsWindow,
    GoblinStatus,
)
from api.core.errors import DomainError
from api.departments.products import ProductExperience, list_products
from api.services.goblin_identity import (
    is_known_goblin_identifier,
    message_matches_goblin,
)

MAX_GOBLINS = 100
MAX_HISTORY_SCAN = 500


class GoblinHistoryRepository(Protocol):
    async def list_history(
        self,
        *,
        user_id: str,
        goblin_id: str,
        scan_limit: int,
    ) -> list[GoblinHistoryEntry]: ...


class GoblinStatsRepository(Protocol):
    async def get_stats(
        self,
        *,
        user_id: str,
        goblin_id: str,
        started_at: datetime,
        ended_at: datetime,
    ) -> dict[str, Optional[float] | int | None]: ...


@dataclass(frozen=True)
class GoblinStatsSnapshot:
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    success_rate: Optional[float]
    average_duration_ms: Optional[float]
    p95_duration_ms: Optional[float]
    total_cost: Optional[float]


class GoblinCatalogRepository(Protocol):
    def list_catalog(self) -> list[ProductExperience]: ...


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _timestamp_sort_key(entry: GoblinHistoryEntry) -> tuple[float, str]:
    return (_utc(entry.timestamp).timestamp(), entry.id)


def _cursor_for(entry: GoblinHistoryEntry) -> str:
    raw = f"{_utc(entry.timestamp).timestamp()}|{entry.id}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str) -> tuple[float, str]:
    padding = "=" * (-len(cursor) % 4)
    try:
        raw = base64.urlsafe_b64decode(f"{cursor}{padding}").decode("utf-8")
        timestamp, entry_id = raw.split("|", 1)
        return float(timestamp), entry_id
    except (ValueError, UnicodeDecodeError) as exc:
        raise DomainError(
            code="GOBLIN_HISTORY_CURSOR_INVALID",
            message="History cursor is invalid",
            status_code=400,
        ) from exc


def _product_to_status(product: ProductExperience) -> GoblinStatus:
    return GoblinStatus(
        id=product.product_id,
        name=product.display_name,
        title=product.surface_title,
        status="active",
        active=True,
        guild=product.department_id.value,
        description=product.description,
    )


def _stats_snapshot_from_entries(entries: list[GoblinHistoryEntry]) -> GoblinStatsSnapshot:
    total = len(entries)
    completed = sum(1 for entry in entries if entry.status != "failed")
    failed = sum(1 for entry in entries if entry.status == "failed")
    return GoblinStatsSnapshot(
        total_tasks=total,
        completed_tasks=completed,
        failed_tasks=failed,
        success_rate=(completed / total) if total else None,
        average_duration_ms=None,
        p95_duration_ms=None,
        total_cost=None,
    )


class ConversationGoblinHistoryRepository:
    async def list_history(
        self,
        *,
        user_id: str,
        goblin_id: str,
        scan_limit: int,
    ) -> list[GoblinHistoryEntry]:
        from api.storage import conversation_store

        entries: list[GoblinHistoryEntry] = []
        conversations = await conversation_store.list_conversations(
            user_id=user_id,
            limit=scan_limit,
        )

        for conversation in conversations:
            last_user_prompt = ""
            for message in conversation.messages:
                if message.role == "user":
                    last_user_prompt = message.content
                    continue
                if message.role != "assistant":
                    continue

                metadata = message.metadata if isinstance(message.metadata, dict) else {}
                if not message_matches_goblin(metadata, goblin_id):
                    continue

                status = metadata.get("status")
                if status not in {"completed", "failed"}:
                    status = "completed"

                timestamp = message.timestamp
                if not isinstance(timestamp, datetime):
                    timestamp = datetime.fromisoformat(str(timestamp))

                try:
                    entries.append(
                        GoblinHistoryEntry(
                            id=message.message_id,
                            goblin_id=goblin_id,
                            task=last_user_prompt or "chat",
                            response=message.content,
                            timestamp=_utc(timestamp),
                            status=status,
                            kpis=(
                                "status:"
                                f"{status} source:chat conversation:{conversation.conversation_id}"
                            ),
                        )
                    )
                except ValidationError as exc:
                    raise DomainError(
                        code="GOBLIN_HISTORY_INVALID",
                        message="Stored goblin history is invalid",
                        status_code=500,
                        details={"reason": str(exc)},
                    ) from exc

        return sorted(entries, key=_timestamp_sort_key, reverse=True)


class ConversationGoblinStatsRepository:
    async def get_stats(
        self,
        *,
        user_id: str,
        goblin_id: str,
        started_at: datetime,
        ended_at: datetime,
    ) -> dict[str, Optional[float] | int | None]:
        from api.storage import conversation_store

        return await conversation_store.get_goblin_stats(
            user_id=user_id,
            goblin_id=goblin_id,
            started_at=started_at,
            ended_at=ended_at,
        )


class ProductCatalogRepository:
    def list_catalog(self) -> list[ProductExperience]:
        return list_products()


@dataclass(frozen=True)
class GoblinHistoryService:
    repository: GoblinHistoryRepository
    user_id: str

    async def get_history(
        self,
        goblin_id: str,
        *,
        limit: int,
        cursor: Optional[str] = None,
    ) -> GoblinHistoryResponse:
        try:
            entries = await self.repository.list_history(
                user_id=self.user_id,
                goblin_id=goblin_id,
                scan_limit=MAX_HISTORY_SCAN,
            )
        except DomainError:
            raise
        except Exception as exc:
            raise DomainError(
                code="GOBLIN_HISTORY_REPOSITORY_FAILED",
                message="Failed to read goblin history",
                status_code=500,
            ) from exc

        entries = sorted(entries, key=_timestamp_sort_key, reverse=True)

        if cursor:
            cursor_key = _decode_cursor(cursor)
            entries = [entry for entry in entries if _timestamp_sort_key(entry) < cursor_key]

        page = entries[:limit]
        next_cursor = _cursor_for(page[-1]) if len(entries) > limit and page else None
        return GoblinHistoryResponse(
            items=page,
            total=len(entries),
            limit=limit,
            next_cursor=next_cursor,
        )


@dataclass(frozen=True)
class GoblinStatsService:
    repository: GoblinStatsRepository
    user_id: str

    async def get_stats(self, goblin_id: str, *, window_hours: int) -> GoblinStatsResponse:
        ended_at = datetime.now(timezone.utc)
        started_at = ended_at - timedelta(hours=window_hours)

        try:
            stats_getter = getattr(self.repository, "get_stats", None)
            if callable(stats_getter):
                snapshot_raw = await stats_getter(
                    user_id=self.user_id,
                    goblin_id=goblin_id,
                    started_at=started_at,
                    ended_at=ended_at,
                )
                snapshot = GoblinStatsSnapshot(
                    total_tasks=int(snapshot_raw.get("total_tasks") or 0),
                    completed_tasks=int(snapshot_raw.get("completed_tasks") or 0),
                    failed_tasks=int(snapshot_raw.get("failed_tasks") or 0),
                    success_rate=(
                        float(snapshot_raw["success_rate"])
                        if snapshot_raw.get("success_rate") is not None
                        else None
                    ),
                    average_duration_ms=(
                        float(snapshot_raw["average_duration_ms"])
                        if snapshot_raw.get("average_duration_ms") is not None
                        else None
                    ),
                    p95_duration_ms=(
                        float(snapshot_raw["p95_duration_ms"])
                        if snapshot_raw.get("p95_duration_ms") is not None
                        else None
                    ),
                    total_cost=(
                        float(snapshot_raw["total_cost"])
                        if snapshot_raw.get("total_cost") is not None
                        else None
                    ),
                )
            else:
                entries = await self.repository.list_history(
                    user_id=self.user_id,
                    goblin_id=goblin_id,
                    scan_limit=MAX_HISTORY_SCAN,
                )
                windowed = [entry for entry in entries if _utc(entry.timestamp) >= started_at]
                snapshot = _stats_snapshot_from_entries(windowed)
        except DomainError:
            raise
        except Exception as exc:
            raise DomainError(
                code="GOBLIN_STATS_REPOSITORY_FAILED",
                message="Failed to read goblin stats",
                status_code=500,
            ) from exc

        return GoblinStatsResponse(
            goblin_id=goblin_id,
            window=GoblinStatsWindow(
                hours=window_hours,
                started_at=started_at,
                ended_at=ended_at,
            ),
            counters=GoblinStatsCounters(
                total_tasks=snapshot.total_tasks,
                completed_tasks=snapshot.completed_tasks,
                failed_tasks=snapshot.failed_tasks,
            ),
            latency=GoblinStatsLatency(
                average_duration_ms=snapshot.average_duration_ms,
                p95_duration_ms=snapshot.p95_duration_ms,
            ),
            success_rate=snapshot.success_rate,
            total_cost=snapshot.total_cost,
        )


@dataclass(frozen=True)
class GoblinQueryService:
    catalog_repository: GoblinCatalogRepository
    history_service: GoblinHistoryService
    stats_service: GoblinStatsService

    async def list_goblins(self) -> GoblinListResponse:
        items = [_product_to_status(product) for product in self.catalog_repository.list_catalog()]
        return GoblinListResponse(items=items[:MAX_GOBLINS], total=len(items), limit=MAX_GOBLINS)

    async def get_history(
        self,
        goblin_id: str,
        *,
        limit: int,
        cursor: Optional[str] = None,
    ) -> GoblinHistoryResponse:
        self._require_known_goblin(goblin_id)
        return await self.history_service.get_history(goblin_id, limit=limit, cursor=cursor)

    async def get_stats(self, goblin_id: str, *, window_hours: int) -> GoblinStatsResponse:
        self._require_known_goblin(goblin_id)
        return await self.stats_service.get_stats(goblin_id, window_hours=window_hours)

    def _require_known_goblin(self, goblin_id: str) -> None:
        if not is_known_goblin_identifier(goblin_id):
            raise DomainError(
                code="GOBLIN_NOT_FOUND",
                message="Goblin not found",
                status_code=404,
                details={"goblin_id": goblin_id},
            )


def build_goblin_query_service(
    *,
    user_id: str,
    history_repository: Optional[GoblinHistoryRepository] = None,
    stats_repository: Optional[GoblinStatsRepository] = None,
    catalog_repository: Optional[GoblinCatalogRepository] = None,
) -> GoblinQueryService:
    history_repo = history_repository or ConversationGoblinHistoryRepository()
    stats_repo = stats_repository or ConversationGoblinStatsRepository()
    catalog_repo = catalog_repository or ProductCatalogRepository()
    return GoblinQueryService(
        catalog_repository=catalog_repo,
        history_service=GoblinHistoryService(repository=history_repo, user_id=user_id),
        stats_service=GoblinStatsService(repository=stats_repo, user_id=user_id),
    )


__all__ = [
    "ConversationGoblinHistoryRepository",
    "ConversationGoblinStatsRepository",
    "GoblinCatalogRepository",
    "GoblinHistoryRepository",
    "GoblinHistoryService",
    "GoblinQueryService",
    "GoblinStatsRepository",
    "GoblinStatsSnapshot",
    "GoblinStatsService",
    "ProductCatalogRepository",
    "build_goblin_query_service",
]
