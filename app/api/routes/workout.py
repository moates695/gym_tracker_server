from fastapi import APIRouter, HTTPException, Security, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import List, Literal
from api.middleware.database import setup_connection
import jwt
import os
from datetime import datetime, timedelta, timezone
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import random
import json

from api.middleware.token import *
from api.routes.auth import verify_token
from api.middleware.misc import *

router = APIRouter()
security = HTTPBearer()

class SetData(BaseModel):
    reps: int
    weight: float | None
    num_sets: int
    set_class: Literal['working', 'dropset', 'warmup', 'cooldown']

class Exercise(BaseModel):
    id: str
    set_data: List[SetData]

class WorkoutSave(BaseModel):
    exercises: List[Exercise]
    start_time: int #? timestamp ms
    duration: int #? ms

@router.post("/workout/save") 
async def workout_save(req: WorkoutSave, credentials: dict = Depends(verify_token)):
    try:
        conn = None
        if len(req.exercises) == 0: return

        conn = await setup_connection()

        start_time = datetime.fromtimestamp(req.start_time / 1000, tz=timezone.utc)
        workout_id = await conn.fetchval(
            """
            insert into workouts
            (user_id, started_at, duration_secs)
            values
            ($1, $2, $3)
            returning id;
            """, credentials["user_id"], start_time, req.duration / 1000
        )

        for i, exercise in enumerate(req.exercises):
            await save_exercise(conn, workout_id, exercise, i)

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Uncaught exception")
    finally:
        if conn: await conn.close()
    return {}

# async def update_body_weights(conn, user_id, exercises: List[Exercise]):
#     if not any(e.is_body_weight for e in exercises): return

#     row = await conn.fetchrow(
#         """
#         select gender, weight
#         from users
#         where id = $1
#         """, user_id
#     )

#     upper_mass_ratio = 0.62 if row["gender"] == "male" else 0.55

#     for exercise in exercises:
#         if not exercise.is_body_weight: continue
#         # todo fetch classification from db table, then compute weight
#         weight = 18.25
#         for set_data in exercise.set_data:
#             set_data.weight = weight

async def save_exercise(conn, workout_id, exercise: Exercise, index): 
    workout_exercise_id = await conn.fetchval(
        """
        insert into workout_exercises
        (workout_id, exercise_id, order_index)
        values
        ($1, $2, $3)
        returning id
        """, workout_id, exercise.id, index
    )

    for j, set_data in enumerate(exercise.set_data):
        await save_set_data(conn, workout_exercise_id, set_data, j)

async def save_set_data(conn, workout_exercise_id, set_data: SetData, index):
    await conn.execute(
        """
        insert into workout_set_data
        (workout_exercise_id, order_index, reps, weight, num_sets, set_class)
        values
        ($1, $2, $3, $4, $5, $6)
        """, workout_exercise_id, index, set_data.reps, set_data.weight, set_data.num_sets, set_data.set_class
    )

# define body weight calc types like: lower leg, full body horizontal, full body pull etc
# async def body_weight_calc(conn, user_id, exercise_id):
#     pass

@router.get("/workout/overview/stats")
async def workout_overview_stats(use_real: bool, credentials: dict = Depends(verify_token)):
    if use_real:
        return await workout_overview_stats_real()
    return await workout_overview_stats_rand()

async def workout_overview_stats_real():
    workouts = []

    return {
        "workouts": workouts
    }

async def workout_overview_stats_rand():
    workouts = []
    for _ in range(random.randint(20, 50)):
        muscles = {}
        with open("app/local/muscles.json", "r") as f:
            muscles_json = json.load(f)

        for group, targets in muscles_json.items():
            if random.random() > 0.6: continue
            muscles[group] = {}
            for target in targets:
                if random.random() > 0.9: continue
                muscles[group][target] = {
                    "volume": random.randint(100,900) + random.random(),
                    "num_sets": random.randint(2,6),
                    "reps": random.randint(15,45)
                }

        workouts.append({
            "started_at": random_timestamp(),
            "duration": random.randint(20, 120) * 60 + random.random(),
            "num_exercises": random.randint(3,10),
            "totals": {
                "volume": random_weight() * random.randint(100, 400),
                "num_sets":  random.randint(3, 20),
                "reps": random.randint(30, 250),
            },
            "muscles": muscles
        })

    workouts = sorted(workouts, key=lambda x: x["started_at"], reverse=True)
    
    return {
        "workouts": workouts
    }

# @router.post("/workout/overview/history")
# async def workout_overview_stats(credentials: dict = Depends(verify_token)):
#     return {}