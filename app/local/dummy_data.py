import json
import asyncio
import os
from fastapi.testclient import TestClient

from ..main import app
from ..api.middleware.database import setup_connection
from ..tests.test_workout_save import build_workouts, save_workouts
from ..api.middleware.auth_token import generate_token

client = TestClient(app)

async def main():
    try:
        conn = await setup_connection()

        user_id = '7a83d775-1f52-4ede-9493-0aac96012cda'
        token = generate_token('moates695@gmail.com', user_id, minutes=5)
        headers = {
            "Authorization": f"Bearer {token}"
        }

        await conn.execute(
            """
            delete
            from workouts
            where user_id = $1
            """, user_id
        )

        workouts = await build_workouts(conn, 100, 200)
        await save_workouts(workouts, headers=headers)

    except Exception as e:
        raise e
    finally:
        if conn: await conn.close()

if __name__ == "__main__":
    asyncio.run(main())