import os
import asyncpg
import asyncio

from .misc import load_env_vars

load_env_vars()

database_config = {
    "database": os.getenv("DATABASE"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT"))
}

async def setup_connection(database: str = None) -> asyncpg.connection.Connection:
    try:
        config = database_config.copy()
        if database != None: config["database"] = database
        return await asyncpg.connect(**config)
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