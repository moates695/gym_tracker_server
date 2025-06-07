from fastapi import APIRouter, HTTPException, Security, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import List, Literal
from api.middleware.database import setup_connection
import jwt
import os
from datetime import datetime, timedelta, timezone
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from api.middleware.token import *
from api.routes.auth import verify_token

router = APIRouter()
security = HTTPBearer()

class SetData(BaseModel):
    reps: int
    weight: float | None
    num_sets: int

class Exercise(BaseModel):
    id: str
    set_data: List[SetData]
    is_body_weight: bool

class WorkoutSave(BaseModel):
    exercises: List[Exercise]
    start_time: int
    duration: int

@router.post("/workout/save")
async def workout_save(req: WorkoutSave, credentials: dict = Depends(verify_token)):
    try:
        conn = None
        if len(req.exercises) == 0: return

        conn = await setup_connection()

        start_time = datetime.fromtimestamp(req.start_time / 1000)
        workout_id = await conn.fetchval(
            """
            insert into workouts
            (user_id, started_at, duration_secs)
            values
            ($1, $2, $3)
            returning id;
            """, credentials["user_id"], start_time, req.duration / 1000
        )

        await update_body_weights(conn, credentials["user_id"], req.exercises)

        for i, exercise in enumerate(req.exercises):
            workout_exercise_id = await save_exercise(conn, workout_id, exercise, i)
            for j, set_data in enumerate(exercise.set_data):
                await save_set_data(conn, workout_exercise_id, set_data, j)

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Uncaught exception")
    finally:
        if conn: await conn.close()

async def update_body_weights(conn, user_id, exercises: List[Exercise]):
    if not any(e.is_body_weight for e in exercises): return

    row = await conn.fetchrow(
        """
        select gender, weight
        from users
        where id = $1
        """, user_id
    )

    upper_mass_ratio = 0.62 if row["gender"] == "male" else 0.55

    for exercise in exercises:
        if not exercise.is_body_weight: continue
        # todo fetch classification from db table, then compute weight
        weight = 18.25
        for set_data in exercise.set_data:
            set_data.weight = weight

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
    return workout_exercise_id

async def save_set_data(conn, workout_exercise_id, set_data: SetData, index):
    await conn.execute(
        """
        insert into workout_set_data
        (workout_exercise_id, order_index, reps, weight, num_sets)
        values
        ($1, $2, $3, $4, $5)
        """, workout_exercise_id, index, set_data.reps, set_data.weight, set_data.num_sets
    )

# define body weight calc types like: lower leg, full body horizontal, full body pull etc
async def body_weight_calc(conn, user_id, exercise_id):
    pass