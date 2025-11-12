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

    await r.delete("volume_leaderboard")
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

    for row in rows:
        for zset, col in overall_map.items():
            await r.zadd(zset, {
                str(row["user_id"]): row[col]
            })
    
    # await r.zadd("leaderboard", {
    #     "user1": 501, 
    #     "user2": 25,
    #     "user3": 850,
    #     "user4": 123,
    #     "user5": 607,
    # })
    # top3 = await r.zrevrange("leaderboard", 0, 2, withscores=True)
    # print(top3)

    # all_entries = await r.zrange("leaderboard", 0, -1)
    # print(all_entries)

    # print(await r.zrange("none", 0, -1))

if __name__ == "__main__":
    asyncio.run(main())