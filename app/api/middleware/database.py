import os
import asyncpg
import asyncio
from dotenv import load_dotenv

from .misc import load_env_vars

async def setup_connection() -> asyncpg.connection.Connection:
    try:
        load_env_vars()
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
    
if __name__ == "__main__":
    async def test_func():
        assert await setup_connection() != None

    asyncio.run(test_func())