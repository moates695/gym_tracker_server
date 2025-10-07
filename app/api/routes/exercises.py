from fastapi import APIRouter, HTTPException, Security, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Literal
import jwt
import os
from datetime import datetime, timedelta, timezone
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import random
from copy import deepcopy
import math
import json

from app.api.middleware.database import setup_connection
from app.api.middleware.auth_token import *
from app.api.routes.auth import verify_token
from app.api.middleware.misc import *

router = APIRouter()
security = HTTPBearer()

# return exercises + user stats for previous set timespan

@router.get("/exercises/list/all")
async def exercises_list_all(use_real: bool, credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()
        tx = conn.transaction()
        await tx.start()

        exercise_rows = await conn.fetch(
            """
            select *, (user_id = $1) as is_custom
            from exercises
            where (
                user_id is null
                or user_id = $1
            )
            and parent_id is null;
            """, credentials["user_id"]
        )

        exercises = []
        for exercise_row in exercise_rows:
            exercise_id = str(exercise_row["id"])
            variation_rows = await conn.fetch(
                """
                select *, (user_id = $1) as is_custom
                from exercises
                where (
                    user_id is null
                    or user_id = $1
                )
                and parent_id = $2;
                """, credentials["user_id"], exercise_row["id"]
            )

            variations = []
            for variation_row in variation_rows:
                variations.append({
                    "id": str(variation_row["id"]),
                    "name": variation_row["name"],
                    "is_body_weight": variation_row["is_body_weight"],
                    "muscle_data": await fetch_exercise_muscle_data(conn, variation_row),
                    "description": variation_row["description"],
                    "weight_type": variation_row["weight_type"],
                    "is_custom": variation_row["is_custom"],
                    "frequency": await fetch_exercise_frequency(use_real, conn, variation_row["id"], credentials["user_id"]),
                })

            exercises.append({
                "id": exercise_id,
                "name": exercise_row["name"],
                "is_body_weight": exercise_row["is_body_weight"],
                "muscle_data": await fetch_exercise_muscle_data(conn, exercise_row),
                "description": exercise_row["description"],
                "weight_type": exercise_row["weight_type"],
                "is_custom": exercise_row["is_custom"],
                "frequency": await fetch_exercise_frequency(use_real, conn, exercise_row["id"], credentials["user_id"]),
                "variations": variations
            })
            if exercise_row["is_body_weight"]:
                exercises[-1]["ratios"] = await fetch_bodyweight_ratios(conn, exercise_id)

        exercises.sort(key=lambda e: e["name"].lower())

        if not use_real:
            for exercise in exercises:
                if random.random() < 0.85: continue
                exercise["is_custom"] = True
                for variation in exercise["variations"]:
                    if random.random() < 0.5: continue
                    variation["is_custom"] = True

        await tx.commit()
        return {
            "exercises": exercises
        }

    except HTTPException as e:
        await tx.rollback()
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        await tx.rollback()
        raise HTTPException(status_code=500, detail="Uncaught exception")
    finally:
        if conn: await conn.close()

async def fetch_exercise_muscle_data(conn, exercise_row):
    muscle_group_rows = await conn.fetch(
        """
        select distinct emd.group_id, emd.group_name
        from exercise_muscle_data emd
        where emd.exercise_id = $1
        """, exercise_row["id"]
    )

    muscle_data = []
    for muscle_group_row in muscle_group_rows:
        muscle_target_rows = await conn.fetch(
            """
            select emd.target_id, emd.target_name, emd.ratio
            from exercise_muscle_data emd
            where emd.exercise_id = $1
            and emd.group_id = $2
            """, exercise_row["id"], muscle_group_row["group_id"]
        )

        target_data = []
        for muscle_target_row in muscle_target_rows:
            target_data.append({
                "target_id": muscle_target_row["target_id"],
                "target_name": muscle_target_row["target_name"],
                "ratio": muscle_target_row["ratio"],
            })

        muscle_data.append({
            "group_id": muscle_group_row["group_id"],
            "group_name": muscle_group_row["group_name"],
            "targets": target_data
        })

    return muscle_data

async def fetch_exercise_frequency(use_real, conn, exercise_id, user_id):
    if use_real:
        return await fetch_exercise_frequency_real(conn, exercise_id, user_id)
    return await fetch_exercise_frequency_rand()

async def fetch_exercise_frequency_real(conn, exercise_id, user_id):
    history_rows = await conn.fetch(
        """
        select workout_id, sum(reps * weight * num_sets) as volume, started_at
        from exercise_history
        where exercise_id = $1
        and user_id = $2
        and started_at at time zone 'utc' >= (now() at time zone 'utc' - interval '28 days')
        group by workout_id, started_at
        order by started_at desc
        """, exercise_id, user_id
    )

    days_past_volume = {}
    for history_row in history_rows:
        days_past = get_days_past(history_row["started_at"])
        if days_past == 0 or days_past > 28: continue
        
        if days_past not in days_past_volume.keys():
            days_past_volume[days_past] = 0
        days_past_volume[days_past] += history_row["volume"]

    return days_past_volume

async def fetch_exercise_frequency_rand():
    days_past_volume = {}
    for _ in range(random.randint(0, 12)):
        days_past_volume[random.randint(1, 28)] = random_weight() * random.randint(3,15) * random.randint(1,4)
    return days_past_volume

def get_days_past(started_at):
    now = datetime.now(timezone.utc)
    return abs(now - started_at.astimezone(timezone.utc)).days

async def fetch_bodyweight_ratios(conn, exercise_id):
    rows = await conn.fetch(
        """
        select ratio, gender
        from bodyweight_exercise_ratios
        where exercise_id = $1
        """, exercise_id
    )

    ratios = {}
    for row in rows:
        ratios[row["gender"]] = row["ratio"]
    return ratios

@router.get("/exercise/history")
async def exercise_history(exercise_id: str, use_real: bool, credentials: dict = Depends(verify_token)):
    if use_real:
        return await exercise_history_real(exercise_id, credentials)
    return await exercise_history_rand()

emptyBaseData = {
    "graph": [],
    "table": {
        "headers": [],
        "rows": []
    }
}

async def exercise_history_real(exercise_id: str, credentials: dict):
    try:
        conn = await setup_connection()

        rows = await conn.fetch(
            """
            select w.id workout_id, wsd.reps, wsd.weight, wsd.num_sets, wsd.order_index set_order_index, w.started_at
            from workout_set_data wsd
            inner join workout_exercises we
            on wsd.workout_exercise_id = we.id
            inner join workouts w
            on we.workout_id = w.id
            where w.user_id = $1
            and we.exercise_id = $2
            order by w.started_at desc, we.order_index, wsd.order_index
            """, credentials["user_id"], exercise_id 
        )

        n_rep_max_all_time = build_n_rep_max_all_time(rows)
        n_rep_max_history = build_n_rep_max_history(rows)
        volume_workout = build_volume_workout(rows)
        volume_timespan = build_volume_timespan(rows)
        history = build_history(rows)
        reps_sets_weight = build_reps_sets_weight(rows)

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Uncaught exception")
    finally:
        if conn: await conn.close()

    return {
        "n_rep_max": {
            "all_time": n_rep_max_all_time,
            "history": n_rep_max_history
        },
        "volume": {
            "workout": volume_workout,
            "timespan": volume_timespan
        },
        "history": history,
        "reps_sets_weight": reps_sets_weight
    }

def build_n_rep_max_all_time(rows):
    n_rep_max_all_time_data = {}
    for row in rows:
        curr_max = n_rep_max_all_time_data.get(row["reps"], {"weight": -math.inf})["weight"]
        if row["weight"] <= curr_max: continue
        n_rep_max_all_time_data[row["reps"]] = {
            "weight": row["weight"],
            "timestamp": datetime_to_timestamp_ms(row["started_at"])
        }

    n_rep_max_all_time_data = dict(sorted(n_rep_max_all_time_data.items()))

    n_rep_max_all_time = deepcopy(emptyBaseData)
    n_rep_max_all_time["table"]["headers"] = ["rep", "weight", "date"]
    for rep, data in n_rep_max_all_time_data.items():
        n_rep_max_all_time["graph"].append({
            "x": rep,
            "y": data["weight"]
        })
        n_rep_max_all_time["table"]["rows"].append({
            "rep": rep,
            "weight": data["weight"],
            "date": timestamp_ms_to_date_str(data["timestamp"])
        })

    return n_rep_max_all_time 

def build_n_rep_max_history(rows):
    n_rep_max_history_data = {}
    for row in rows:
        if row["reps"] not in n_rep_max_history_data.keys():
            n_rep_max_history_data[row["reps"]] = {}
        timestamp = datetime_to_timestamp_ms(row["started_at"])
        curr_weight = n_rep_max_history_data[row["reps"]].get(timestamp, -math.inf)
        if curr_weight >= row["weight"]: continue
        n_rep_max_history_data[row["reps"]][timestamp] = row["weight"]

    n_rep_max_history_data = dict(sorted(n_rep_max_history_data.items()))

    n_rep_max_history = {}
    for rep, data in n_rep_max_history_data.items():
        temp_history = deepcopy(emptyBaseData)
        temp_history["table"]["headers"] = ["weight", "date"]

        for timestamp, weight in data.items():
            temp_history["graph"].append({
                "x": timestamp,
                "y": weight
            })
            temp_history["table"]["rows"].append({
                "weight": weight,
                "date": timestamp
            })

        temp_history["graph"] = sort_timeseries(temp_history["graph"], "x")
        temp_history["table"]["rows"] = sort_timeseries(temp_history["table"]["rows"], "date", True)

        n_rep_max_history[rep] = temp_history

    return n_rep_max_history

def build_volume_workout(rows):
    volume_data = volume_per_workout(rows)

    volume = deepcopy(emptyBaseData)
    volume["table"]["headers"] = ["volume", "date"]
    for data in volume_data.values():
        volume["graph"].append({
            "x": data["timestamp"],
            "y": data["volume"]
        })
        volume["table"]["rows"].append({
            "volume": data["volume"],
            "date": data["timestamp"]
        })

    volume["graph"] = sort_timeseries(volume["graph"], "x")
    volume["table"]["rows"] = sort_timeseries(volume["table"]["rows"], "date", True)

    return volume

def build_volume_timespan(rows):
    volume_data = volume_per_workout(rows)

    timespan_data = {}    
    now_ms = datetime.now(tz=timezone.utc).timestamp() * 1000
    for timespan in ["week","month","3_months","6_months","year"]:  
        timespan_ms = timespan_to_ms(timespan)
        bucket_data = {}
        for workout_data in volume_data.values():
            bucket = int((now_ms - workout_data["timestamp"]) / timespan_ms)
            if bucket not in bucket_data:
                bucket_data[bucket] = 0
            bucket_data[bucket] += workout_data["volume"]
        timespan_data[timespan] = dict(sorted(bucket_data.items()))

    volume_timespan = {}
    for timespan, bucket_data in timespan_data.items():
        timespan_ms = timespan_to_ms(timespan)
        temp_data = deepcopy(emptyBaseData)
        temp_data["table"]["headers"] = ["volume", "dates"]
        for bucket, volume in bucket_data.items():
            upper_timestamp = now_ms - bucket * timespan_ms
            lower_timestamp = now_ms - (bucket + 1) * timespan_ms

            temp_data["graph"].append({
                "x": upper_timestamp,
                "y": volume
            })
            temp_data["table"]["rows"].append({
                "volume": volume,
                "dates": f"{timestamp_ms_to_date_str(lower_timestamp)}-{timestamp_ms_to_date_str(upper_timestamp)}"
            })

        volume_timespan[timespan] = temp_data

    return volume_timespan

def volume_per_workout(rows):
    volume_data = {}
    for row in rows:
        if row["workout_id"] not in volume_data:
            volume_data[row["workout_id"]] = {
                "volume": 0,
                "timestamp": datetime_to_timestamp_ms(row["started_at"])
            }
        volume_data[row["workout_id"]]["volume"] += row["reps"] * row["weight"] * row["num_sets"]
    return volume_data

def timespan_to_ms(timespan):
    day_ms = 24 * 60 * 60 * 1000
    week_ms = 7 * day_ms
    month_ms = 30.43 * day_ms
    month_3_ms = 3 * month_ms
    month_6_ms = 2 * month_3_ms
    year_ms = 365.25 * day_ms

    match timespan:
        case 'week':
            return week_ms
        case 'month':
            return month_ms
        case '3_months':
            return month_3_ms
        case '6_months':
            return month_6_ms
        case 'year':
            return year_ms
        case _:
            raise Exception(f"unknown timespan '{timespan}'")

def build_history(rows):
    history_data = {}
    for row in rows:
        if row["workout_id"] not in history_data:
            history_data[row["workout_id"]] = {
                "graph": {
                    "weight_per_set": [],
                    "volume_per_set": [],
                    "weight_per_rep": [],
                },
                "table": {
                    "headers": ["reps", "weight", "sets"],
                    "rows": []
                },
                "started_at": date_to_timestamp_ms(row["started_at"]),
            }

        graph = history_data[row["workout_id"]]["graph"]
        prev_set_idx = 0 if len(graph["weight_per_set"]) == 0 else graph["weight_per_set"][-1]["x"] + 1
        for i in range(row["num_sets"]):
            graph["weight_per_set"].append({
                "x": prev_set_idx + i,
                "y": row["weight"]
            })

            graph["volume_per_set"].append({
                "x": prev_set_idx + i,
                "y": row["reps"] * row["weight"] * row["num_sets"]
            })

            prev_rep_idx = 0 if len(graph["weight_per_rep"]) == 0 else graph["weight_per_rep"][-1]["x"] + 1
            for j in range(row["reps"]):
                graph["weight_per_rep"].append({
                    "x": prev_rep_idx + j,
                    "y": row["weight"]
                })
        
        history_data[row["workout_id"]]["table"]["rows"].append({
            "reps": row["reps"],
            "weight": row["weight"],
            "sets": row["num_sets"]
        })
    
    return sorted(history_data.values(), key=lambda e: e["started_at"], reverse=True)

def build_reps_sets_weight(rows):
    points = []
    for row in rows:
        points.append({
            "x": row["reps"],
            "y": row["weight"],
            "z": row["num_sets"]
        })
    return points

async def exercise_history_rand():
    # now = datetime.now(timezone.utc).timestamp() * 1000

    emptyBaseData = {
        "graph": [],
        "table": {
            "headers": [],
            "rows": []
        }
    }

    history_data = {
        "n_rep_max": {
            "all_time": deepcopy(emptyBaseData),
            "history": {}
        },
        "volume":  {
            "workout": deepcopy(emptyBaseData),
            "timespan": {
                "week": deepcopy(emptyBaseData),
                "month": deepcopy(emptyBaseData),
                "3_months": deepcopy(emptyBaseData),
                "6_months": deepcopy(emptyBaseData),
                "year": deepcopy(emptyBaseData),
            }
        },
        "history": [],
        "reps_sets_weight": []
    }

    if random.random() < 0.05: return history_data

    reps = set([random.randint(1,25) for _ in range(random.randint(1,15))])
    num_workouts = random.randint(1,50)

    n_rep_max_all_time = history_data["n_rep_max"]["all_time"]
    n_rep_max_all_time["table"]["headers"] = ["rep", "weight", "date"]

    for rep in reps:
        n_rep_max_all_time["graph"].append({
            "x": rep,
            "y": random_weight()
        })
        n_rep_max_all_time["table"]["rows"].append({
            "rep": rep,
            "weight": random_weight(),
            "date": timestamp_ms_to_date_str(random_timestamp_ms())
        })

        tempRepHistory = deepcopy(emptyBaseData)
        tempRepHistory["table"]["headers"] = ["weight", "date"]
        for _ in range(random.randint(1, num_workouts)):
            weight = random_weight()
            timestamp = random_timestamp_ms()
            tempRepHistory["graph"].append({
                "x": timestamp,
                "y": weight
            })
            tempRepHistory["table"]["rows"].append({
                "weight": weight,
                "date": timestamp
            })

        tempRepHistory["graph"] = sort_timeseries(tempRepHistory["graph"], "x")
        tempRepHistory["table"]["rows"] = sort_timeseries(tempRepHistory["table"]["rows"], "date", True)
        
        history_data["n_rep_max"]["history"][rep] = tempRepHistory

    volume_workout = history_data["volume"]["workout"]
    volume_workout["table"]["headers"] = ["volume", "date"]

    for _ in range(num_workouts):
        volume = random_volume()
        timestamp = random_timestamp_ms()
        volume_workout["graph"].append({
            "x": timestamp,
            "y": volume
        })
        volume_workout["table"]["rows"].append({
            "volume": volume,
            "date": timestamp
        })

    volume_workout["graph"] = sort_timeseries(volume_workout["graph"], "x")
    volume_workout["table"]["rows"] = sort_timeseries(volume_workout["table"]["rows"], "date", True)


    bucket_nums = set()
    while len(bucket_nums) <= len(history_data["volume"]["timespan"].values()):
        bucket_nums.add(random.randint(1, 50))
    bucket_nums = list(bucket_nums)
    bucket_nums.reverse()

    for i, timespan_value in enumerate(history_data["volume"]["timespan"].values()):
        timespan_value["table"]["headers"] = ["volume", "date"]
        for _ in range(bucket_nums[i]):
            volume = random_volume()
            timestamp = random_timestamp_ms()
            timespan_value["graph"].append({
                "x": timestamp,
                "y": volume
            })
            timespan_value["table"]["rows"].append({
                "volume": volume,
                "date": timestamp
            })

        timespan_value["graph"] = sort_timeseries(timespan_value["graph"], "x")
        timespan_value["table"]["rows"] = sort_timeseries(timespan_value["table"]["rows"], "date", True)

    for _ in range(num_workouts):
        temp_history = {
            "graph": {
                "weight_per_set": [],
                "volume_per_set": [],
                "weight_per_rep": [],
            },
            "table": {
                "headers": ["reps", "weight", "sets"],
                "rows": []
            },
            "started_at": random_timestamp_ms()
        }

        num_sets = random.randint(2,4)
        set_idx = 0
        rep_idx = 0
        for _ in range(num_sets):
            num_reps = random.randint(3,15)
            weight = random_weight()
            volume = weight * num_reps
            for _ in range(num_reps):
                temp_history["graph"]["weight_per_rep"].append({
                    "x": rep_idx,
                    "y": weight
                })

                rep_idx += 1

            temp_history["graph"]["weight_per_set"].append({
                "x": set_idx,
                "y": weight
            })
            temp_history["graph"]["volume_per_set"].append({
                "x": set_idx,
                "y": volume
            })

            temp_history["table"]["rows"].append({
                "reps": num_reps,
                "weight": weight,
                "sets": random.randint(1,3)
            })

            set_idx += 1

        history_data["history"].append(temp_history)

    history_data["history"] = sort_timeseries(history_data["history"], "started_at", True)

    history_data["reps_sets_weight"] = generate_rand_3D_points()

    return history_data

def sort_timeseries(data, key, convert_timestamp=False):
    series = sorted(data, key=lambda e: e[key], reverse=True)
    if not convert_timestamp: return series
    for elem in series:
        elem[key] = timestamp_ms_to_date_str(elem[key])
    return series

def timestamp_ms_to_date_str(timestamp_ms):
    return datetime.fromtimestamp(timestamp_ms / 1000).strftime("%d/%m/%Y")

def generate_rand_3D_points():
    length = random.randint(3, 50)

    weight = random.randint(60, 100)
    reps = random.randint(4, 6)
    sets = random.randint(2, 3)

    data = []
    for _ in range(length):
        data.append({"x": reps, "y": weight, "z": sets})

        reps += random.choice([1, 2])       
        sets += random.choice([0, 1])       
        weight -= random.randint(2, 5)      

        if weight < 20:
            weight = 20
        if sets > 6:
            sets = 6

    return data