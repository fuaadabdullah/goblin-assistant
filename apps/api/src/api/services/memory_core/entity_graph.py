"""Entity graph logic for relationship metadata extraction and persistence."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...storage.vector_models import MemoryEntityModel, MemoryEntityRelationModel
from .models import EntityType, MemoryKind, RelationType

_METADATA_KEY_TO_ENTITY_TYPE: Dict[str, str] = {
    "project": EntityType.PROJECT.value,
    "decision": EntityType.DECISION.value,
    "task": EntityType.TASK.value,
    "workflow": EntityType.PROJECT.value,
    "conversation": EntityType.CONVERSATION.value,
    "user": EntityType.USER.value,
    "person": EntityType.PERSON.value,
    "company": EntityType.COMPANY.value,
    "tool": EntityType.TOOL.value,
    "preference": EntityType.PREFERENCE.value,
    "document": EntityType.DOCUMENT.value,
}

_MEMORY_KIND_TO_ENTITY_TYPE: Dict[MemoryKind, str] = {
    MemoryKind.FACT: EntityType.DOCUMENT.value,
    MemoryKind.PREFERENCE: EntityType.PREFERENCE.value,
    MemoryKind.DECISION: EntityType.DECISION.value,
    MemoryKind.PROJECT_STATE: EntityType.PROJECT.value,
    MemoryKind.RELATIONSHIP: EntityType.PERSON.value,
    MemoryKind.TASK_SIGNAL: EntityType.TASK.value,
}


def _normalize_entity_type(raw_type: str) -> str:
    """Map a raw entity type string to a canonical EntityType value."""
    normalized = raw_type.lower().removesuffix("_id")
    if normalized in _METADATA_KEY_TO_ENTITY_TYPE:
        return _METADATA_KEY_TO_ENTITY_TYPE[normalized]
    try:
        return EntityType(normalized).value
    except ValueError:
        return EntityType.DOCUMENT.value


def _derive_relation_type(entity_type: str, memory_kind: MemoryKind) -> str:
    """Derive a RelationType for a subject→entity edge based on entity type and memory kind."""
    if entity_type == EntityType.CONVERSATION.value:
        return RelationType.CREATED_FROM.value
    if entity_type == EntityType.PROJECT.value:
        return RelationType.BELONGS_TO.value
    if entity_type == EntityType.DECISION.value:
        return (
            RelationType.DEPENDS_ON.value
            if memory_kind == MemoryKind.TASK_SIGNAL
            else RelationType.SUPPORTS.value
        )
    return RelationType.REFERS_TO.value


def _extract_entity_refs(metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    refs: List[Dict[str, Any]] = []
    for key in ("project_id", "decision_id", "task_id", "workflow_id", "conversation_id"):
        value = metadata.get(key)
        if value:
            entity_type = _normalize_entity_type(key)
            refs.append({"type": entity_type, "value": str(value)})
    for item in metadata.get("entity_refs") or []:
        if isinstance(item, dict) and item.get("value"):
            raw_type = str(item.get("type") or "entity")
            refs.append(
                {
                    "type": _normalize_entity_type(raw_type),
                    "value": str(item["value"]),
                    "confidence": float(item.get("confidence", 1.0)),
                }
            )
        elif item:
            refs.append({"type": EntityType.DOCUMENT.value, "value": str(item), "confidence": 1.0})
    return refs


def _extract_related_ids(metadata: Dict[str, Any]) -> List[str]:
    related = []
    for key in ("related_memory_ids", "related_ids", "links"):
        value = metadata.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    related.append(item.strip())
                elif isinstance(item, dict) and item.get("target"):
                    related.append(str(item["target"]))
    return sorted(set(related))


async def _persist_entity_graph(
    session: Any,
    *,
    user_id: str,
    memory_fact_id: str,
    entity_refs: List[Dict[str, Any]],
    related_memory_ids: List[str],
    memory_type: MemoryKind,
    scope: str,
) -> None:
    """Persist entity nodes and relation edges for a memory fact.

    Called inside an open session after the MemoryFactModel row is flushed.
    Upserts entity nodes (by user_id+type+value uniqueness) and inserts
    typed relation edges from a subject entity to each referenced entity.
    """
    from sqlalchemy import select as _select  # noqa: PLC0415

    async def _upsert_entity(
        entity_type: str, entity_value: str, confidence: float = 1.0
    ) -> Optional[str]:
        result = await session.execute(
            _select(MemoryEntityModel).where(
                MemoryEntityModel.user_id == user_id,
                MemoryEntityModel.entity_type == entity_type,
                MemoryEntityModel.entity_value == entity_value,
            )
        )
        existing_entity = result.scalar_one_or_none()
        if existing_entity is not None:
            return existing_entity.id
        import uuid as _uuid  # noqa: PLC0415

        new_entity = MemoryEntityModel(
            id=str(_uuid.uuid4()),
            user_id=user_id,
            entity_type=entity_type,
            entity_value=entity_value,
            scope=scope,
            confidence=confidence,
        )
        session.add(new_entity)
        await session.flush()
        return new_entity.id

    # Upsert the subject entity representing this memory fact
    subject_entity_type = _MEMORY_KIND_TO_ENTITY_TYPE.get(memory_type, EntityType.DOCUMENT.value)
    subject_entity_id = await _upsert_entity(subject_entity_type, memory_fact_id)
    if subject_entity_id is None:
        return

    import uuid as _uuid  # noqa: PLC0415

    # Upsert target entities and create edges from subject → target
    for ref in entity_refs:
        ref_type = str(ref.get("type") or EntityType.DOCUMENT.value)
        ref_value = str(ref.get("value", ""))
        ref_confidence = float(ref.get("confidence", 1.0))
        if not ref_value:
            continue
        target_entity_id = await _upsert_entity(ref_type, ref_value, ref_confidence)
        if target_entity_id and target_entity_id != subject_entity_id:
            relation_type = _derive_relation_type(ref_type, memory_type)
            session.add(
                MemoryEntityRelationModel(
                    id=str(_uuid.uuid4()),
                    user_id=user_id,
                    source_entity_id=subject_entity_id,
                    target_entity_id=target_entity_id,
                    relation_type=relation_type,
                    memory_fact_id=memory_fact_id,
                    confidence=ref_confidence,
                )
            )

    # Create LINKED_TO edges for sibling memory facts
    for sibling_id in related_memory_ids:
        if not sibling_id:
            continue
        sibling_entity_type = subject_entity_type
        sibling_entity_id = await _upsert_entity(sibling_entity_type, sibling_id)
        if sibling_entity_id and sibling_entity_id != subject_entity_id:
            session.add(
                MemoryEntityRelationModel(
                    id=str(_uuid.uuid4()),
                    user_id=user_id,
                    source_entity_id=subject_entity_id,
                    target_entity_id=sibling_entity_id,
                    relation_type=RelationType.LINKED_TO.value,
                    memory_fact_id=memory_fact_id,
                    confidence=1.0,
                )
            )

    await session.flush()
