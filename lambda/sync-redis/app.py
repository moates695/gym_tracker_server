import asyncio
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

from shared.helpers import db_connection, redis_connection, load_secrets

load_dotenv(override=True)

#! need to provide secret name and keys to include from it (redis password gets overwritten)
load_secrets({
    "prod/gym-junkie/api": ['REDIS_PASSWORD']
})

# todo: could use redis mapping from misc.py? (what if misc includes async funcs?)

def handler(event, context):
    try:
        r = redis_connection()
        if not r.ping(): raise Exception("cannot connect to redis")
        
        conn, cur = db_connection()

        sync_overall(r, conn, cur)
        sync_exercises(r, conn, cur)

    except Exception as e:
        print(e)
        return {"ok": False}
    
    return {"ok": True} 

def sync_overall(r, conn, cur):
    overall_map = {
        "overall:volume:leaderboard": "volume",
        "overall:sets:leaderboard": "num_sets",
        "overall:reps:leaderboard": "reps",
        "overall:exercises:leaderboard": "num_exercises",
        "overall:workouts:leaderboard": "num_workouts",
        "overall:duration:leaderboard": "duration_mins",
    }

    for key in overall_map.keys():
        r.delete(key)

    cur.execute(
        """
        select *
        from overall_leaderboard
        """
    )
    rows = cur.fetchall()

    for row in rows:
        for zset, column in overall_map.items():
            r.zadd(zset, {
                str(row["user_id"]): row[column]
            })

def sync_exercises(r, conn, cur):
    cur.execute(
        """
        select id
        from exercises
        """
    )
    rows = cur.fetchall() 
    
    for row in rows:
        sync_exercise(r, conn, cur, row["id"])

def sync_exercise(r, conn, cur, exercise_id):
    column_map = { #? redis key: column
        "volume": "volume",
        "sets": "num_sets",
        "reps": "reps",
        "workouts": "num_workouts",
    }
    key_name = "exercise:{exercise_id}:{metric}:leaderboard"

    for metric in column_map.keys():
        r.delete(key_name.format(
            exercise_id=exercise_id, 
            metric=metric
        ))

    cur.execute(
        """
        select *
        from exercises_leaderboard
        where exercise_id = %s
        """, [exercise_id]
    )
    rows = cur.fetchall()

    for row in rows:
        for metric, column in column_map.items():
            r.zadd(key_name.format(
                exercise_id=exercise_id, 
                metric=metric
            ), {
                str(row["user_id"]): row[column]
            })
