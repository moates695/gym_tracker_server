import asyncio
import json

from ..api.middleware.database import setup_connection

async def load_exercises():
    try:
        conn = await setup_connection()

        with open("app/local/exercises.json", "r") as file:
            exercises = json.load(file)

        for exercise in exercises:
            await conn.execute(
                """
                insert into exercises
                (name, is_body_weight)
                values
                ($1, $2)
                """, exercise["name"], exercise["is_body_weight"]
            )
       
    except Exception as e:
        print(e)
    finally:
        if conn: await conn.close()

async def load_muscle_groups():
    return

async def main():
    await load_exercises()

if __name__ == "__main__":
    asyncio.run(main())