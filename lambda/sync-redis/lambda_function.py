import logging
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
import psycopg2 as pg
import psycopg2.extras
import redis
import os
import boto3
import requests 

load_dotenv(override=True)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    try:
        # load_secrets({
        #     # "prod/gym-junkie/api": ['REDIS_PASSWORD']
        #     "prod/gym-junkie/postgres": []
        # })

        r = redis.Redis(host="172.31.2.32", port=6379)
        if not r.ping(): raise Exception("cannot connect to redis")

        num = r.zcard("test")
        logging.info(num)

        secret_name = "arn:aws:secretsmanager:us-east-1:111122223333:secret:SECRET_NAME"
        secrets_extension_endpoint = f"http://localhost:2773/secretsmanager/get?secretId={secret_name}"
        headers = {"X-Aws-Parameters-Secrets-Token": os.environ.get('AWS_SESSION_TOKEN')}

        response = requests.get(secrets_extension_endpoint, headers=headers)
        print(f"Response status code: {response.status_code}")

        secret = json.loads(response.text)["SecretString"]
        print(f"Retrieved secret: {secret}")

        conn, cur = db_connection()

    except Exception as e:
        logger.error(str(e))

    return {"status": "ok"}

def db_connection():
    conn = cur = None
    try:
        conn = pg.connect(
            dbname=os.environ["DATABASE"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            host=os.environ["DB_HOST"],
            port=os.environ["DB_PORT"]
        )
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    except Exception as e:
        print(e)
    return conn, cur

def redis_connection():
    r = None
    try:
        r = redis.Redis(
            host=os.environ["REDIS_HOST"],
            port=os.environ["REDIS_PORT"],
            password=os.environ["REDIS_PASSWORD"],
            decode_responses=True
        )
    except Exception as e:
        print(e)
    return r

def load_secrets(secrets):
    if os.environ["ENVIRONMENT"] != "prod": return

    region = os.environ.get('AWS_REGION', 'ap-southeast-2')

    for name, keys in secrets.items(): 
        try:
            client = boto3.client('secretsmanager', region_name=region)
            response = client.get_secret_value(SecretId=name)
            secrets = json.loads(response['SecretString'])
            
            for key, value in secrets.items():
                if keys != [] and key not in keys: continue
                os.environ[key] = str(value)
            
        except Exception as e:
            print(f"Error loading secret: {e}")
            raise

# def handler(event, context):
#     try:
#         print("here445")
#         return {"ok": True}

#         load_secrets({
#             "prod/gym-junkie/api": ['REDIS_PASSWORD']
#         })

#         r = redis_connection()
#         if not r.ping(): raise Exception("cannot connect to redis")
        
#         return {"ok": True} 


#         conn, cur = db_connection()

#         sync_overall(r, conn, cur)
#         sync_exercises(r, conn, cur)

#     except Exception as e:
#         print(e)
#         return {"ok": False}
    
#     return {"ok": True} 

# def sync_overall(r, conn, cur):
#     overall_map = {
#         "overall:volume:leaderboard": "volume",
#         "overall:sets:leaderboard": "num_sets",
#         "overall:reps:leaderboard": "reps",
#         "overall:exercises:leaderboard": "num_exercises",
#         "overall:workouts:leaderboard": "num_workouts",
#         "overall:duration:leaderboard": "duration_mins",
#     }

#     for key in overall_map.keys():
#         r.delete(key)

#     cur.execute(
#         """
#         select *
#         from overall_leaderboard
#         """
#     )
#     rows = cur.fetchall()

#     for row in rows:
#         for zset, column in overall_map.items():
#             r.zadd(zset, {
#                 str(row["user_id"]): row[column]
#             })

# def sync_exercises(r, conn, cur):
#     cur.execute(
#         """
#         select id
#         from exercises
#         """
#     )
#     rows = cur.fetchall() 
    
#     for row in rows:
#         sync_exercise(r, conn, cur, row["id"])

# def sync_exercise(r, conn, cur, exercise_id):
#     column_map = { #? redis key: column
#         "volume": "volume",
#         "sets": "num_sets",
#         "reps": "reps",
#         "workouts": "num_workouts",
#     }
#     key_name = "exercise:{exercise_id}:{metric}:leaderboard"

#     for metric in column_map.keys():
#         r.delete(key_name.format(
#             exercise_id=exercise_id, 
#             metric=metric
#         ))

#     cur.execute(
#         """
#         select *
#         from exercises_leaderboard
#         where exercise_id = %s
#         """, [exercise_id]
#     )
#     rows = cur.fetchall()

#     for row in rows:
#         for metric, column in column_map.items():
#             r.zadd(key_name.format(
#                 exercise_id=exercise_id, 
#                 metric=metric
#             ), {
#                 str(row["user_id"]): row[column]
#             })
