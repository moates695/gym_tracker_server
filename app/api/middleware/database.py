import os
import psycopg2 as pg
import logging

database_config = {
    "dbname": os.getenv("DATABASE"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT"))
}

def setup_connection():
    try:
        conn = cur = None
        conn = pg.connect(**database_config)
        cur = conn.cursor()
    except Exception as e:
        logging.error(f"Error in db connection setup: {e}")
    return conn, cur