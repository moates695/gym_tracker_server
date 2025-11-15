import asyncio
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
 
from ..api.middleware.database import *

load_dotenv(override=True)

async def main():
    r = await redis_connection()
    if not await r.ping(): raise Exception("cannot connect to redis")
    
    conn = await setup_connection()

    await sync_overall(r, conn)

async def sync_overall(r, conn):
    overall_map = {
        "overall:volume:leaderboard": "volume",
        "overall:sets:leaderboard": "num_sets",
        "overall:reps:leaderboard": "reps",
        "overall:exercises:leaderboard": "num_exercises",
        "overall:workouts:leaderboard": "num_workouts",
        "overall:duration:leaderboard": "duration_mins",
    }

    for key in overall_map.keys():
        await r.delete(key)

    rows = await conn.fetch(
        """
        select *
        from overall_leaderboard
        """
    )

    for row in rows:
        for zset, column in overall_map.items():
            await r.zadd(zset, {
                str(row["user_id"]): row[column]
            })

async def sync_exercises(r, conn):
    rows = await conn.fetch(
        """
        select id
        from exercises
        """
    )

    for row in rows:
        await sync_exercise(r, conn, row["id"])

async def sync_exercise(r, conn, exercise_id):
    column_map = { #? redis: column
        "volume": "volume",
        "sets": "num_sets",
        "reps": "reps",
        "workouts": "num_workouts",
    }
    key_name = "exercise:{exercise_id}:{metric}:leaderboard"
    for metric in column_map.keys():
        await r.delete(key_name.format(exercise_id, metric))

    rows = await conn.fetch(
        """
        select *
        from exercises_leaderboard
        where exercise_id = $1
        """, exercise_id
    )
    for row in rows:
        for metric, column in column_map.items():
            await r.zadd(key_name.format(exercise_id, metric), {
                str(row["user_id"]): row[column]
            })

if __name__ == "__main__":
    asyncio.run(main())