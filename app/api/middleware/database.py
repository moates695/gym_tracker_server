import os
import asyncpg

database_config = {
    "database": os.getenv("DATABASE"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT"))
}

async def setup_connection():
    try:
        conn = await asyncpg.connect(**database_config)
    except Exception as e:
        raise Exception(f"Error in db connection setup: {e}")
    return conn