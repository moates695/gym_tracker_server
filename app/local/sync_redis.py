import asyncio
import json
from datetime import datetime, timezone

from ..api.middleware.misc import load_env_vars 
from ..api.middleware.database import *

load_env_vars()

async def main():
    r = await redis_connection()
    print(await r.ping())
    

    # await r.delete("volume_leaderboard")
    await r.zadd("leaderboard", {
        "user1": 501, 
        "user2": 25,
        "user3": 850,
        "user4": 123,
        "user5": 607,
    })
    top3 = await r.zrevrange("leaderboard", 0, 2, withscores=True)
    print(top3)

    all_entries = await r.zrange("leaderboard", 0, -1)
    print(all_entries)

    print(await r.zrange("none", 0, -1))

if __name__ == "__main__":
    asyncio.run(main())