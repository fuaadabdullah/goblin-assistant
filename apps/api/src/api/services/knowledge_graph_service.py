"""Knowledge graph service for querying entity relationships and building user profiles."""

from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import select

from ..storage.vector_models import MemoryEntityModel, MemoryEntityRelationModel
from .memory_core.models import EntityType


class UserProfileSnapshot:
    """Snapshot of a user's profile distilled from the entity graph."""

    def __init__(self):
        self.goals: List[str] = []
        self.projects: List[str] = []
        self.preferences: Dict[str, Any] = {}
        self.key_entities: Dict[str, List[Dict[str, Any]]] = {}

    def to_dict(self) -> dict:
        return {
            "goals": self.goals,
            "projects": self.projects,
            "preferences": self.preferences,
            "key_entities": self.key_entities,
        }


class KnowledgeGraphService:
    """Query the entity graph to extract structured user intelligence."""

    def __init__(self, session_factory=None):
        self.session_factory = session_factory

    async def get_entity_clusters(
        self,
        user_id: str,
        session=None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get all entities for a user, grouped by type.

        For each entity, fetch its outgoing relations and related facts.

        Returns:
            dict[entity_type, list[entity_obj]]
            where entity_obj = {
                "value": str,
                "confidence": float,
                "display_name": str,
                "relations": [{"target_value": str, "relation_type": str, "confidence": float}]
            }
        """

        close_session = False
        if session is None:
            if not self.session_factory:
                raise ValueError("session_factory required if session not provided")
            session = self.session_factory()
            close_session = True

        try:
            # Fetch all entities for this user
            entities_result = await session.execute(
                select(MemoryEntityModel).where(MemoryEntityModel.user_id == user_id)
            )
            entities = entities_result.scalars().all()

            clusters: Dict[str, List[Dict[str, Any]]] = {}

            for entity in entities:
                entity_type = entity.entity_type
                if entity_type not in clusters:
                    clusters[entity_type] = []

                # Fetch outgoing relations for this entity
                relations_result = await session.execute(
                    select(MemoryEntityRelationModel, MemoryEntityModel).where(
                        MemoryEntityRelationModel.source_entity_id == entity.id
                    )
                )
                relations = relations_result.all()

                entity_obj: Dict[str, Any] = {
                    "value": entity.entity_value,
                    "confidence": entity.confidence or 1.0,
                    "display_name": entity.display_name or entity.entity_value,
                    "relations": [],
                }

                for rel, target_entity in relations:
                    if target_entity:
                        entity_obj["relations"].append(
                            {
                                "target_value": target_entity.entity_value,
                                "target_type": target_entity.entity_type,
                                "relation_type": rel.relation_type,
                                "confidence": rel.confidence or 1.0,
                            }
                        )

                clusters[entity_type].append(entity_obj)

            return clusters
        finally:
            if close_session:
                await session.close()

    async def build_profile_snapshot(
        self,
        user_id: str,
        session=None,
    ) -> UserProfileSnapshot:
        """Build a structured user profile snapshot from entity clusters.

        Distils entities into typed buckets:
        - goals: tasks with high confidence
        - projects: project entities
        - preferences: preference entities with their values
        - key_entities: instruments, companies, persons with relations
        """
        snapshot = UserProfileSnapshot()

        # Get entity clusters
        clusters = await self.get_entity_clusters(user_id, session)

        # Extract goals from TASK entities
        if EntityType.TASK.value in clusters:
            snapshot.goals = [
                e["value"]
                for e in clusters[EntityType.TASK.value]
                if e.get("confidence", 1.0) > 0.5
            ][:5]

        # Extract projects
        if EntityType.PROJECT.value in clusters:
            snapshot.projects = [
                e["value"]
                for e in clusters[EntityType.PROJECT.value]
                if e.get("confidence", 1.0) > 0.5
            ][:5]

        # Extract preferences
        if EntityType.PREFERENCE.value in clusters:
            for pref in clusters[EntityType.PREFERENCE.value]:
                snapshot.preferences[pref["value"]] = pref.get("display_name", pref["value"])

        # Extract key entities (non-document types with relations)
        for entity_type in [
            EntityType.COMPANY.value,
            EntityType.PERSON.value,
            EntityType.TOOL.value,
        ]:
            if entity_type in clusters:
                snapshot.key_entities[entity_type] = [
                    {
                        "value": e["value"],
                        "confidence": e.get("confidence", 1.0),
                        "relations": e.get("relations", []),
                    }
                    for e in clusters[entity_type]
                ][:10]

        return snapshot
