import random
from datetime import datetime, timezone
from typing import Literal
from pydantic import Field
from dotenv import load_dotenv
import os

def random_weight():
    return random.randint(1, 200) + random.choice([0, .25, .5, .75])

def random_timestamp():
    now = datetime.now(timezone.utc).timestamp() * 1000
    delta = 1000 * 60 * 60 * 24 * random.randint(1, 400)
    return now - delta

def datetime_to_timestamp_ms(dt):
    return int(dt.timestamp() * 1000)

def date_to_timestamp_ms(date):
    return int(datetime.combine(date, datetime.min.time()).timestamp() * 1000)

email_field = Field(pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
password_field = Field(min_length=8, max_length=36)
name_field = Field(min_length=1, max_length=255)
gender_literal = Literal["male", "female", "other"]
height_field = Field(ge=0, le=500)
weight_field = Field(ge=0, le=500)
goal_status_literal = Literal["bulking", "cutting", "maintaining"]
ped_status_literal = Literal["natural", "juicing", "silent"]

user_data_to_tables = [
    {
        "key": 'first_name',
        "table": 'users',
        "column": 'first_name',
    },
    {
        "key": 'last_name',
        "table": 'users',
        "column": 'last_name',
    },
    {
        "key": 'gender',
        "table": 'users',
        "column": 'gender',
    },
    {
        "key": 'height',
        "table": 'user_heights',
        "column": 'height',
    },
    {
        "key": 'weight',
        "table": 'user_weights',
        "column": 'weight',
    },
    {
        "key": 'goal_status',
        "table": 'user_goals',
        "column": 'goal_status',
    },
    {
        "key": 'ped_status',
        "table": 'user_ped_status',
        "column": 'ped_status',
    },
]

def get_user_data_map(key: str):
    for data_map in user_data_to_tables:
        if data_map["key"] != key: continue
        return data_map
    
def load_env_vars():
    os.environ.clear()
    load_dotenv(dotenv_path="app/envs/.env", override=True)
    load_dotenv(dotenv_path=f"app/envs/{os.environ['ENVIRONMENT']}.env", override=True)