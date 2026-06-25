import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def enable_vector():
    db_url = "postgresql+asyncpg://postgres:3ZeErPfTdYu%23adzhKDEs@db.dhxoowakvmobjxsffpst.supabase.co:5432/postgres?sslmode=require"
    engine = create_async_engine(db_url)

    try:
        async with engine.begin() as conn:
            print("Attempting to enable pgvector extension...")
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            print("Successfully enabled pgvector (or it was already enabled).")
    except Exception as e:
        print(f"Failed to enable pgvector: {e}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(enable_vector())
