import random
from datetime import datetime, timezone
from typing import Literal, get_args
from pydantic import Field
from dotenv import load_dotenv
import os

def random_weight():
    return random.randint(1, 200) + random.choice([0, .25, .5, .75])

def random_volume():
    volume = 0
    for _ in range(3,15):
        volume += random_weight() * random.randint(2,4)
    return volume

def random_timestamp_ms():
    now = now_timestamp_ms()
    delta = 1000 * 60 * 60 * 24 * random.randint(1, 1000)
    return now - delta

def now_timestamp_ms():
    return int(datetime.now(tz=timezone.utc).timestamp() * 1000)

def datetime_to_timestamp_ms(dt):
    return int(dt.timestamp() * 1000)

def date_to_timestamp_ms(date):
    return int(datetime.combine(date, datetime.min.time()).timestamp() * 1000)

email_field = Field(pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
password_field = Field(min_length=8, max_length=36)
name_field = Field(min_length=0, max_length=255)
gender_literal = Literal["male", "female", "other"]
height_field = Field(ge=0, le=500)
weight_field = Field(ge=0, le=500)
goal_status_literal = Literal["bulking", "cutting", "maintaining"]
ped_status_literal = Literal["natural", "juicing", "silent"]
    
user_data_tables_map = {
    "first_name": {
        "table": 'users',
        "column": 'first_name',
    },
    "last_name": {
        "table": 'users',
        "column": 'last_name',
    },
    "gender": {
        "table": 'users',
        "column": 'gender',
    },
    "height": {
        "table": 'user_heights',
        "column": 'height',
    },
    "weight": {
        "table": 'user_weights',
        "column": 'weight',
    },
    "goal_status": {
        "table": 'user_goals',
        "column": 'goal_status',
    },
    "ped_status": {
        "table": 'user_ped_status',
        "column": 'ped_status',
    }
}
 
overall_leaderboard_literal = Literal["volume", "sets", "reps", "exercises", "workouts", "duration"]
overall_leaderboard_metrics = list(get_args(overall_leaderboard_literal))
overall_column_map = {
    "volume": "volume",
    "sets": "num_sets",
    "reps": "reps",
    "exercises": "num_exercises",
    "workouts": "num_workouts",
    "duration": "duration_mins",
}
def overall_zset_name(metric):
    return f"overall:{metric}:leaderboard"

exercise_leaderboard_literal = Literal["volume", "sets", "reps", "workouts"]
exercise_leaderboard_metrics = list(get_args(exercise_leaderboard_literal))
exercise_column_map = {
    "volume": "volume",
    "sets": "num_sets",
    "reps": "reps",
    "workouts": "num_workouts",
}
def exercise_zset_name(exercise_id, metric):
    return f"exercise:{exercise_id}:{metric}:leaderboard"

class SafeError(Exception):
    """Error with a message safe to show to the client."""
    pass