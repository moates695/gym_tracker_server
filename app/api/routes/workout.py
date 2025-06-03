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
    weight: float
    num_sets: int

class Exercise(BaseModel):
    id: str
    set_data: List[SetData]

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
        
        for i, exercise in enumerate(req.exercises):
            await save_exercise(conn, workout_id, exercise, i)

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Uncaught exception")
    finally:
        if conn: await conn.close()

async def save_exercise(conn, workout_id, exercise: Exercise, index): 
    workout_exercise_id = await conn.fetchval(
        """
        insert into workout_exercises
        (workout_id, exercise_id, order_index)
        values
        ($1, $2, $3)
        """, workout_id, exercise.id, index
    )
    print(workout_exercise_id)