import psycopg2 as pg
import redis
from dotenv import load_dotenv
import os
import psycopg2.extras
import boto3
import json

load_dotenv(override=True)

# todo: pass in logger and print exception to it

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