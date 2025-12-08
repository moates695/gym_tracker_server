import redis
import psycopg2 as pg
import psycopg2.extras
from dotenv import load_dotenv
import os
import logging
import sys
import threading

load_dotenv()

def main():
    thread = threading.Thread(target=sync)
    thread.daemon = True
    thread.start()
    thread.join(timeout=60)

    if thread.is_alive(): raise TimeoutError("sync timed out")

def sync():
    try:
        r = redis_connection()
        if not r.ping(): return

        conn, cur = db_connection()

        sync_overall(r, conn, cur)
        sync_exercises(r, conn, cur)

        print("done")

    except Exception as e:
        print(str(e))

def redis_connection():
    r = None
    try:
        r = redis.Redis(
            host=os.environ["REDIS_HOST"],
            port=os.environ["REDIS_PORT"],
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    except Exception as e:
        print(e)
    return r

def db_connection():
    conn = cur = None
    try:
        conn = pg.connect(
            dbname=os.environ["DATABASE"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            host=os.environ["DB_HOST"],
            port=os.environ["DB_PORT"],
            connect_timeout=5
        )
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    except Exception as e:
        print(e)
    return conn, cur

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

if __name__ == "__main__":
    main()