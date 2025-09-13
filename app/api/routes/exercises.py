from fastapi import APIRouter, HTTPException, Security, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from api.middleware.database import setup_connection
import jwt
import os
from datetime import datetime, timedelta, timezone
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import random
from copy import deepcopy

from api.middleware.auth_token import *
from api.routes.auth import verify_token
from api.middleware.misc import *

router = APIRouter()
security = HTTPBearer()

# return exercises + user stats for previous set timespan

@router.get("/exercises/list/all")
async def exercises_list_all(use_real: bool, credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()

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
                "id": str(exercise_row["id"]),
                "name": exercise_row["name"],
                "is_body_weight": exercise_row["is_body_weight"],
                "muscle_data": await fetch_exercise_muscle_data(conn, exercise_row),
                "description": exercise_row["description"],
                "weight_type": exercise_row["weight_type"],
                "is_custom": exercise_row["is_custom"],
                "frequency": await fetch_exercise_frequency(use_real, conn, exercise_row["id"], credentials["user_id"]),
                "variations": variations
            })

        exercises.sort(key=lambda e: e["name"].lower())

        if not use_real:
            for exercise in exercises:
                if random.random() < 0.85: continue
                exercise["is_custom"] = True
                for variation in exercise["variations"]:
                    if random.random() < 0.5: continue
                    variation["is_custom"] = True

        return {
            "exercises": exercises
        }

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
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

@router.get("/exercise/history")
async def exercise_history(exercise_id: str, use_real: bool, credentials: dict = Depends(verify_token)):
    if use_real:
        return await exercise_history_real(exercise_id, credentials)
    return await exercise_history_rand()

async def exercise_history_real(exercise_id: str, credentials: dict):
    try:
        conn = await setup_connection()
        
        rows = await conn.fetch(
            """
            select wsd.reps, wsd.weight, wsd.num_sets, wsd.created_at
            from workouts w
            inner join workout_exercises we
            on we.workout_id = w.id
            inner join workout_set_data wsd
            on wsd.workout_exercise_id = we.id
            where w.user_id = $1
            and we.exercise_id = $2
            order by wsd.created_at desc
            """, credentials["user_id"], exercise_id 
        )

        n_rep_max_all_time = {}
        for row in rows:
            if n_rep_max_all_time.get(row["reps"], {"weight": 0})["weight"] < row["weight"]: continue
            n_rep_max_all_time[row["reps"]] = {
                "weight": row["weight"],
                "timestamp": datetime_to_timestamp_ms(row["created_at"])
            }

        n_rep_max_history = {}
        for row in rows:
            if row["reps"] not in n_rep_max_history.keys():
                n_rep_max_history[row["reps"]] = []
            n_rep_max_history[row["reps"]].append({
                "weight": row["weight"],
                "timestamp": datetime_to_timestamp_ms(row["created_at"])
            })

        # for rep, history in n_rep_max_history.items():
        #     n_rep_max_history[rep] = sorted(history, key=lambda x: x["timestamp"])

        volume_days = {}
        for row in rows:
            date = row["created_at"].date()
            if date not in volume_days.keys():
                volume_days[date] = 0
            volume_days[date] += row["reps"] * row["weight"] * row["num_sets"]

        volume = [{
            "volume": value,
            "timestamp": date_to_timestamp_ms(key)
        } for key, value in volume_days.items()]
        volume = sorted(volume, key=lambda x: x["timestamp"], reverse=True)

        history_days = {}
        for row in rows:
            date = row["created_at"].date()
            if date not in history_days.keys():
                history_days[date] = []
            history_days[date].append({
                "reps": row[0],
                "weight": row[1],
                "num_sets": row[2],
            })

        history = [{
            "set_data": value,
            "timestamp": date_to_timestamp_ms(key)
        } for key, value in history_days.items()]
        history = sorted(history, key=lambda x: x["timestamp"], reverse=True)

        reps_sets_weight = []
        for row in rows:
            reps_sets_weight.append({
                "reps": row[0],
                "weight": row[1],
                "num_sets": row[2],
            })

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
        "volume": volume,
        "history": history,
        "reps_sets_weight": reps_sets_weight,
    }

async def exercise_history_rand():
    # now = datetime.now(timezone.utc).timestamp() * 1000

    emptyBaseData = {
        "graph": [],
        "table": {
            "header": [],
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
        "history": {
            "weight_per_set": deepcopy(emptyBaseData),
            "volume_per_set": deepcopy(emptyBaseData),+
            "weight_per_rep": deepcopy(emptyBaseData),
        },
        "reps_sets_weight": []
    }

    if random.random() < 0.05: return history_data
    
    reps = set([random.randint(1,25) for _ in range(random.randint(1,15))])
    num_workouts = random.randint(1,50)

    n_rep_max_all_time = history_data["n_rep_max"]["all_time"]
    n_rep_max_all_time["table"]["header"] = ["rep", "weight", "date"]

    for rep in reps:
        n_rep_max_all_time["graph"].append({
            "x": rep,
            "y": random_weight()
        })
        n_rep_max_all_time["table"]["rows"].append({
            "rep": rep,
            "weight": random_weight(),
            "date": random_timestamp_ms()
        })

        tempRepHistory = deepcopy(emptyBaseData)
        tempRepHistory["table"]["headers"] = ["weight", "date"]
        for _ in range(num_workouts):
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

        sort_timeseries(tempRepHistory["graph"], "x")
        sort_timeseries(tempRepHistory["table"]["rows"], "date")

        # tempRepHistory["graph"] = sorted(
        #     tempRepHistory["graph"],
        #     key=lambda x: x["x"],
        #     reverse=True
        # )

        # tempRepHistory["table"]["rows"] = sorted(
        #     tempRepHistory["table"]["rows"],
        #     key=lambda x: x["date"],
        #     reverse=True
        # )
        
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

    # volume_workout["graph"] = sorted(
    #     volume_workout["graph"],
    #     key=lambda x: x["x"],
    #     reverse=True
    # )
    sort_timeseries(volume_workout["graph"], "x")


    # volume_workout["table"]["rows"] = sorted(
    #     volume_workout["table"]["rows"],
    #     key=lambda x: x["date"],
    #     reverse=True
    # )
    sort_timeseries(volume_workout["table"]["rows"], "date")


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

        sort_timeseries(timespan_value["graph"], "x")
        sort_timeseries(timespan_value["table"]["rows"], "date")

        # timespan_value["graph"] = sorted(
        #     timespan_value["graph"],
        #     key=lambda x: x["x"],
        #     reverse=True
        # )

        # timespan_value["table"]["rows"] = sorted(
        #     timespan_value["table"]["rows"],
        #     key=lambda x: x["date"],
        #     reverse=True
        # )

    for _ in range(num_workouts):
        num_sets = random.randint(3, 16)
        num_reps = num_sets * random.randint(3, 15)



    history_data["reps_sets_weight"] = generate_rand_3D_points()

    # todo: order timestamp series (if order required)

    return history_data

def sort_timeseries(data, key):
    data = sorted(data, key=lambda e: e[key], reverse=True)

def generate_rand_3D_points():
    length = random.randint(3, 50)

    # start with higher weight, lower reps/sets
    weight = random.randint(60, 100)
    reps = random.randint(4, 6)
    sets = random.randint(2, 3)

    data = []
    for _ in range(length):
        data.append({"x": reps, "y": weight, "z": sets})

        # enforce trend:
        # as reps × sets increases → weight decreases
        reps += random.choice([1, 2])       # slowly increase reps
        sets += random.choice([0, 1])       # sometimes add a set
        weight -= random.randint(2, 5)      # gradually drop weight

        # clamp values
        if weight < 20:
            weight = 20
        if sets > 6:
            sets = 6

    return data

    # n_rep_max_all_time = {}
    # n_rep_max_history = {}
    # for rep in reps:
    #     n_rep_max_all_time[rep] = {
    #         "weight": random_weight(),
    #         "timestamp": random_timestamp()
    #     }

    #     history = []
    #     used_days = []
    #     for _ in range(random.randint(5,20)):
    #         while _:
    #             day = random.randint(1,400)
    #             if day in used_days: continue
    #             used_days.append(day)
    #             break
            
    #         history.append({
    #             "weight": random_weight(),
    #             "timestamp": random_timestamp()
    #         })

    #     history = sorted(history, key=lambda x: x["timestamp"], reverse=True)
    #     n_rep_max_history[rep] = history

    # volume = []
    # for _ in range(0, random.randint(20,30)):
    #     volume.append({
    #         "value": random_weight() * random.randint(2, 4),
    #         "timestamp": random_timestamp()
    #     })

    # volume = sorted(volume, key=lambda x: x["timestamp"], reverse=True)

    # history = []
    # for _ in range(random.randint(15,20)):
    #     set_data = []
    #     for _ in range(random.randint(3,15)):
    #         set_data.append({
    #             "reps": random.randint(5,15),
    #             "weight": random_weight(),
    #             "num_sets": random.randint(1,4)
    #         })

    #     history.append({
    #         "set_data": set_data,
    #         "timestamp": random_timestamp()
    #     })

    # history = sorted(history, key=lambda x: x["timestamp"], reverse=True)

    # reps_sets_weight = []
    # for _ in range(random.randint(5,40)):
    #     reps_sets_weight.append({
    #         "reps": random.randint(5,15),
    #         "weight": random_weight(),
    #         "num_sets": random.randint(1,5)
    #     })

    # return {
    #     "n_rep_max": {
    #         "all_time": n_rep_max_all_time,
    #         "history": n_rep_max_history
    #     }, 
    #     "volume": volume,
    #     "history": history,
    #     "reps_sets_weight": reps_sets_weight,
    # }