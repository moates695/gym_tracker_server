import asyncio
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

from ..api.middleware.misc import load_env_vars 
from ..api.middleware.database import *

# load_env_vars()
load_dotenv(override=True)

async def main():
    r = await redis_connection()
    if not await r.ping(): raise Exception("cannot connect to redis")
    
    conn = await setup_connection()

    rows = await conn.fetch(
        """
        select *
        from overall_leaderboard
        """
    )
    
    overall_map = {
        "overall_volume": "volume",
        "overall_sets": "num_sets",
        "overall_reps": "reps",
        "overall_exercises": "num_exercises",
        "overall_workouts": "num_workouts",
        "overall_duration": "duration_mins",
    }

    for key in overall_map.keys():
        await r.delete(key)

    for row in rows:
        for zset, col in overall_map.items():
            await r.zadd(zset, {
                str(row["user_id"]): row[col]
            })

if __name__ == "__main__":
    asyncio.run(main())