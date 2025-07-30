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

from api.middleware.token import *
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
            where user_id is null
            or user_id = $1
            """, credentials["user_id"]
        )

        exercises = []
        for exercise_row in exercise_rows:
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

            exercises.append({
                "id": str(exercise_row["id"]),
                "name": exercise_row["name"],
                "is_body_weight": exercise_row["is_body_weight"],
                "muscle_data": muscle_data,
                "description": exercise_row["description"],
                "weight_type": exercise_row["weight_type"],
                "is_custom": exercise_row["is_custom"],
                "frequency": await fetch_exercise_frequency(use_real, conn, exercise_row["id"], credentials["user_id"])
            })

        exercises.sort(key=lambda e: e["name"].lower())

        for exercise in exercises:
            if random.random() < 0.85: continue
            exercise["is_custom"] = True

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
            if n_rep_max_all_time.get(row["reps"], {"weight": 0})["weight"] >= row["weight"]: continue
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

        for rep, history in n_rep_max_history.items():
            n_rep_max_history[rep] = sorted(history, key=lambda x: x["timestamp"])

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
        volume = sorted(volume, key=lambda x: x["timestamp"])

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
        history = sorted(history, key=lambda x: x["timestamp"])

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
    now = datetime.now(timezone.utc).timestamp() * 1000
    
    reps = set([random.randint(1,25) for _ in range(20)])
    
    n_rep_max_all_time = {}
    n_rep_max_history = {}
    for rep in reps:
        n_rep_max_all_time[rep] = {
            "weight": random_weight(),
            "timestamp": random_timestamp()
        }

        history = []
        used_days = []
        for _ in range(random.randint(5,20)):
            while _:
                day = random.randint(1,400)
                if day in used_days: continue
                used_days.append(day)
                break
            
            history.append({
                "weight": random_weight(),
                "timestamp": random_timestamp()
            })

        history = sorted(history, key=lambda x: x["timestamp"])
        n_rep_max_history[rep] = history

    volume = []
    for _ in range(0, random.randint(20,30)):
        volume.append({
            "value": random_weight() * random.randint(2, 4),
            "timestamp": random_timestamp()
        })

    volume = sorted(volume, key=lambda x: x["timestamp"])

    history = []
    for _ in range(random.randint(15,20)):
        set_data = []
        for _ in range(random.randint(3,15)):
            set_data.append({
                "reps": random.randint(5,15),
                "weight": random_weight(),
                "num_sets": random.randint(1,4)
            })

        history.append({
            "set_data": set_data,
            "timestamp": random_timestamp()
        })

    history = sorted(history, key=lambda x: x["timestamp"], reverse=True)

    reps_sets_weight = []
    for _ in range(random.randint(5,40)):
        reps_sets_weight.append({
            "reps": random.randint(5,15),
            "weight": random_weight(),
            "num_sets": random.randint(1,5)
        })

    return {
        "n_rep_max": {
            "all_time": n_rep_max_all_time,
            "history": n_rep_max_history
        }, 
        "volume": volume,
        "history": history,
        "reps_sets_weight": reps_sets_weight,
    }