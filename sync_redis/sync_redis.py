import redis
import psycopg2 as pg
import psycopg2.extras
from dotenv import load_dotenv
import os
import logging
import sys
import threading
import asyncio
import time
from datetime import datetime

from database import setup_connection, redis_connection
from misc import *

load_dotenv()

async def main():
    thread = threading.Thread(target=sync_runner)
    thread.daemon = True
    thread.start()
    thread.join(timeout=60)

    if thread.is_alive(): raise TimeoutError("sync timed out")

def sync_runner():
    asyncio.run(sync())

async def sync():
    start = time.time()
    try:
        r = await redis_connection()
        if not await r.ping(): 
            raise Exception("could not reach redis")

        conn = await setup_connection()

        await sync_overall(r, conn)
        await sync_exercises(r, conn)

        print(f"{datetime.now().isoformat()}: {(time.time() - start):.3f} secs")

    except Exception as e:
        print(str(e))

async def sync_overall(r, conn):
    rows = await conn.fetch(
        """
        select *
        from overall_leaderboard
        """
    )

    for metric, column in overall_column_map.items():
        zset = overall_zset_name(metric)
        await r.delete(zset)
        for row in rows:
            await r.zadd(
                zset, 
                {str(row["user_id"]): row[column]}
            )

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
    rows = await conn.fetch(
        """
        select *
        from exercises_leaderboard
        where exercise_id = $1
        """, exercise_id
    )

    for metric, column in exercise_column_map.items():
        zset = exercise_zset_name(exercise_id, metric)
        await r.delete(exercise_zset_name(exercise_id, metric))
        for row in rows:
            await r.zadd(
                zset, 
                {str(row["user_id"]): row[column]}
            )

if __name__ == "__main__":
    asyncio.run(main())