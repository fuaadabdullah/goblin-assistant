"""
Benchmark memory seeder.

Seeds controlled facts into the database under an isolated test user,
and cleans up afterwards. The test user is created with a deterministic
ID derived from the run_id so concurrent benchmark runs don't collide.

Usage is always via runner.py, not directly.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


async def _create_bench_user(session: Any, user_id: str) -> None:
    """Insert a minimal user row so FK constraints are satisfied."""
    from sqlalchemy import text  # noqa: PLC0415

    await session.execute(
        text(
            "INSERT OR IGNORE INTO users (id, email, name, is_active, created_at, updated_at)"
            " VALUES (:id, :email, :name, 1, :now, :now)"
        ),
        {
            "id": user_id,
            "email": f"bench-{user_id[:8]}@benchmark.internal",
            "name": f"Benchmark User {user_id[:8]}",
            "now": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        },
    )
    await session.commit()


async def _create_bench_user_pg(session: Any, user_id: str) -> None:
    """PostgreSQL version of test user creation (ON CONFLICT DO NOTHING)."""
    from sqlalchemy import text  # noqa: PLC0415

    await session.execute(
        text(
            "INSERT INTO users (id, email, name, is_active, created_at, updated_at)"
            " VALUES (:id, :email, :name, true, :now, :now)"
            " ON CONFLICT (id) DO NOTHING"
        ),
        {
            "id": user_id,
            "email": f"bench-{user_id[:8]}@benchmark.internal",
            "name": f"Benchmark User {user_id[:8]}",
            "now": datetime.now(timezone.utc).replace(tzinfo=None),
        },
    )
    await session.commit()


async def create_bench_user(user_id: str) -> None:
    from api.storage.database import DATABASE_URL, get_db_context  # noqa: PLC0415

    async with get_db_context() as session:
        if "postgresql" in DATABASE_URL:
            await _create_bench_user_pg(session, user_id)
        else:
            await _create_bench_user(session, user_id)


async def delete_bench_user(user_id: str) -> int:
    """Delete the test user and cascade-delete all their facts."""
    from sqlalchemy import text  # noqa: PLC0415

    from api.storage.database import get_db_context  # noqa: PLC0415

    deleted = 0
    async with get_db_context() as session:
        # Delete facts first (no cascade in SQLite)
        r1 = await session.execute(
            text("DELETE FROM memory_facts WHERE user_id = :uid"),
            {"uid": user_id},
        )
        deleted += r1.rowcount
        r2 = await session.execute(
            text("DELETE FROM users WHERE id = :uid"),
            {"uid": user_id},
        )
        deleted += r2.rowcount
        await session.commit()
    return deleted


class SeedResult:
    """Maps scenario fact_ids to their DB-assigned UUIDs after seeding."""

    def __init__(self) -> None:
        self.fact_id_to_db_id: Dict[str, str] = {}
        self.db_id_to_fact_id: Dict[str, str] = {}
        self.failed: List[str] = []

    def register(self, fact_id: str, db_id: str) -> None:
        self.fact_id_to_db_id[fact_id] = db_id
        self.db_id_to_fact_id[db_id] = fact_id

    def lookup_fact_id(self, db_id: str) -> Optional[str]:
        return self.db_id_to_fact_id.get(db_id)

    def lookup_db_id(self, fact_id: str) -> Optional[str]:
        return self.fact_id_to_db_id.get(fact_id)


async def seed_scenario(
    scenario: Dict[str, Any],
    user_id: str,
    seed_result: SeedResult,
    *,
    verbose: bool = False,
) -> None:
    """Seed all facts from one scenario for the given user."""
    from api.services.memory_core import memory_core_service  # noqa: PLC0415

    facts = scenario.get("facts", [])
    # Sort by seed_order if present (for contradiction scenarios where order matters)
    facts = sorted(facts, key=lambda f: f.get("seed_order", 0))

    for fact in facts:
        fact_id = fact["fact_id"]
        try:
            record = await memory_core_service.ingest_memory_fact(
                user_id=user_id,
                fact_text=fact["text"],
                category=fact.get("category", "general"),
                metadata={
                    "benchmark": True,
                    "scenario_id": scenario["scenario_id"],
                    "scenario_fact_id": fact_id,
                    "tags": fact.get("tags", []),
                },
                source_kind="benchmark",
                confidence=0.9,
            )
            if record and record.id:
                seed_result.register(fact_id, record.id)
                if verbose:
                    print(f"    seeded {fact_id} → {record.id[:8]}")
            else:
                seed_result.failed.append(fact_id)
                if verbose:
                    print(f"    FAILED {fact_id} (no record returned)")
        except Exception as exc:
            seed_result.failed.append(fact_id)
            logger.warning(
                "memory_bench_seed_failed",
                fact_id=fact_id,
                error=str(exc),
            )
            if verbose:
                print(f"    ERROR {fact_id}: {exc}")

        # Small delay between facts to preserve ordering (for contradiction tests)
        await asyncio.sleep(0.05)


async def seed_all(
    scenarios: List[Dict[str, Any]],
    user_id: str,
    *,
    verbose: bool = False,
) -> SeedResult:
    """Seed all scenarios and return the fact-id mapping."""
    result = SeedResult()

    if verbose:
        print(f"  Creating test user {user_id[:16]}...")
    await create_bench_user(user_id)

    for scenario in scenarios:
        if verbose:
            n = len(scenario["facts"])
            print(f"  Seeding scenario '{scenario['scenario_id']}' ({n} facts)...")
        await seed_scenario(scenario, user_id, result, verbose=verbose)

    total = len(result.fact_id_to_db_id)
    failed = len(result.failed)
    if verbose:
        print(f"  Seeded {total} facts, {failed} failed.")
    if result.failed:
        logger.warning("memory_bench_seed_partial", failed=result.failed)

    return result
