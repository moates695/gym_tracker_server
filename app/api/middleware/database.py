import os
import asyncpg
import asyncio
from dotenv import load_dotenv
from redis import asyncio as aioredis

load_dotenv(override=True)

async def setup_connection() -> asyncpg.connection.Connection:
    try:
        return await asyncpg.connect(**{
            "database": os.getenv("DATABASE"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST"),
            "port": int(os.getenv("DB_PORT"))
        })

    except Exception as e:
        print(e)
        import traceback
        print("Error connecting to database:")
        traceback.print_exc()
        return None
    
async def redis_connection():
    try:
        redis_url = f"redis://:{os.environ['REDIS_PASSWORD']}@{os.environ['REDIS_HOST']}:{os.environ['REDIS_PORT']}"
        return await aioredis.from_url(
            redis_url,
            encoding='utf-8',
            decode_responses=True
        )
    except Exception as e:
        print(e)
        import traceback
        print("Error connecting to database:")
        traceback.print_exc()
        return None

if __name__ == "__main__":
    async def test_func():
        assert await setup_connection() != None

    asyncio.run(test_func())