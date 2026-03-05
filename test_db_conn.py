import asyncio
import os
from api.storage.database import init_db
from dotenv import load_dotenv


async def test_db():
    load_dotenv(".env.local")
    print(f"DATABASE_URL: {os.getenv('DATABASE_URL')}")
    try:
        success = await init_db()
        print(f"DB Init Success: {success}")
    except Exception as e:
        print(f"DB Init Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_db())
