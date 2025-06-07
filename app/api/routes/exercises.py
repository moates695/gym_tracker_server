from fastapi import APIRouter, HTTPException, Security, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from api.middleware.database import setup_connection
import jwt
import os
from datetime import datetime, timedelta, timezone
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from api.middleware.token import *
from api.routes.auth import verify_token

router = APIRouter()
security = HTTPBearer()

# return exercises + user stats for previous set timespan

@router.get("/exercises/list/all")
async def exercises_list_all(credentials: dict = Depends(verify_token)):
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
                "weight_type": exercise_row["weight_type"]
            })

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

@router.get("/exercise/history")
async def exercise_history(id: str, credentials: dict = Depends(verify_token)):
    now = datetime.now(timezone.utc).timestamp() * 1000
    return {
        "n_rep_max": {
            "all_time": {
                "1": { "weight": 155.8, "timestamp": now - 1000 * 60 * 60 * 24 * 30 },
                "3": { "weight": 152.9, "timestamp": now - 1000 * 60 * 60 * 24 * 180 },
                "5": { "weight": 143.2, "timestamp": now - 1000 * 60 * 60 * 24 * 90 },
                "10": { "weight": 135.6, "timestamp": now - 1000 * 60 * 60 * 24 * 14 },
                "11": { "weight": 133.5, "timestamp": now - 1000 * 60 * 60 * 24 * 7 },
                "20": { "weight": 90.9, "timestamp": now - 1000 * 60 * 60 * 24 * 400 }
            },
            "history": {
                "1": [
                    { "weight": 148.6, "timestamp": now - 1000 * 60 * 60 * 24 * 1 },
                    { "weight": 149.0, "timestamp": now - 1000 * 60 * 60 * 24 * 3 },
                    { "weight": 148.6, "timestamp": now - 1000 * 60 * 60 * 24 * 5 },
                    { "weight": 152.2, "timestamp": now - 1000 * 60 * 60 * 24 * 10 },
                    { "weight": 151.0, "timestamp": now - 1000 * 60 * 60 * 24 * 20 },
                    { "weight": 155.8, "timestamp": now - 1000 * 60 * 60 * 24 * 30 },
                    { "weight": 150.8, "timestamp": now - 1000 * 60 * 60 * 24 * 60 },
                    { "weight": 150.5, "timestamp": now - 1000 * 60 * 60 * 24 * 80 },
                    { "weight": 153.7, "timestamp": now - 1000 * 60 * 60 * 24 * 150 },
                    { "weight": 153.7, "timestamp": now - 1000 * 60 * 60 * 24 * 300 },
                    { "weight": 148.1, "timestamp": now - 1000 * 60 * 60 * 24 * 370 }
                ],
                "3": [
                    { "weight": 141.0, "timestamp": now - 1000 * 60 * 60 * 24 * 2 },
                    { "weight": 148.5, "timestamp": now - 1000 * 60 * 60 * 24 * 10 },
                    { "weight": 146.2, "timestamp": now - 1000 * 60 * 60 * 24 * 20 },
                    { "weight": 142.9, "timestamp": now - 1000 * 60 * 60 * 24 * 40 },
                    { "weight": 145.1, "timestamp": now - 1000 * 60 * 60 * 24 * 60 },
                    { "weight": 143.9, "timestamp": now - 1000 * 60 * 60 * 24 * 90 },
                    { "weight": 149.9, "timestamp": now - 1000 * 60 * 60 * 24 * 180 },
                    { "weight": 149.4, "timestamp": now - 1000 * 60 * 60 * 24 * 250 },
                    { "weight": 144.7, "timestamp": now - 1000 * 60 * 60 * 24 * 300 }
                ],
                "5": [
                    { "weight": 138.2, "timestamp": now - 1000 * 60 * 60 * 24 * 1 },
                    { "weight": 137.0, "timestamp": now - 1000 * 60 * 60 * 24 * 3 },
                    { "weight": 140.2, "timestamp": now - 1000 * 60 * 60 * 24 * 5 },
                    { "weight": 139.9, "timestamp": now - 1000 * 60 * 60 * 24 * 10 },
                    { "weight": 141.5, "timestamp": now - 1000 * 60 * 60 * 24 * 40 },
                    { "weight": 143.2, "timestamp": now - 1000 * 60 * 60 * 24 * 75 },
                    { "weight": 139.7, "timestamp": now - 1000 * 60 * 60 * 24 * 90 },
                    { "weight": 142.6, "timestamp": now - 1000 * 60 * 60 * 24 * 180 },
                    { "weight": 140.8, "timestamp": now - 1000 * 60 * 60 * 24 * 365 }
                ],
                "10": [
                    { "weight": 128.1, "timestamp": now - 1000 * 60 * 60 * 24 * 1 },
                    { "weight": 121.5, "timestamp": now - 1000 * 60 * 60 * 24 * 7 },
                    { "weight": 128.4, "timestamp": now - 1000 * 60 * 60 * 24 * 14 },
                    { "weight": 130.0, "timestamp": now - 1000 * 60 * 60 * 24 * 20 },
                    { "weight": 126.7, "timestamp": now - 1000 * 60 * 60 * 24 * 30 },
                    { "weight": 129.6, "timestamp": now - 1000 * 60 * 60 * 24 * 50 },
                    { "weight": 129.1, "timestamp": now - 1000 * 60 * 60 * 24 * 90 },
                    { "weight": 122.6, "timestamp": now - 1000 * 60 * 60 * 24 * 180 },
                    { "weight": 125.8, "timestamp": now - 1000 * 60 * 60 * 24 * 365 }
                ],
                "11": [
                    { "weight": 118.9, "timestamp": now - 1000 * 60 * 60 * 24 * 3 },
                    { "weight": 126.5, "timestamp": now - 1000 * 60 * 60 * 24 * 7 },
                    { "weight": 120.4, "timestamp": now - 1000 * 60 * 60 * 24 * 15 },
                    { "weight": 124.1, "timestamp": now - 1000 * 60 * 60 * 24 * 30 },
                    { "weight": 118.6, "timestamp": now - 1000 * 60 * 60 * 24 * 45 },
                    { "weight": 117.6, "timestamp": now - 1000 * 60 * 60 * 24 * 90 },
                    { "weight": 123.7, "timestamp": now - 1000 * 60 * 60 * 24 * 180 },
                    { "weight": 119.7, "timestamp": now - 1000 * 60 * 60 * 24 * 270 },
                    { "weight": 122.9, "timestamp": now - 1000 * 60 * 60 * 24 * 400 }
                ],
                "20": [
                    { "weight": 91.8, "timestamp": now - 1000 * 60 * 60 * 24 * 14 },
                    { "weight": 94.4, "timestamp": now - 1000 * 60 * 60 * 24 * 45 },
                    { "weight": 93.7, "timestamp": now - 1000 * 60 * 60 * 24 * 60 },
                    { "weight": 92.3, "timestamp": now - 1000 * 60 * 60 * 24 * 90 },
                    { "weight": 96.7, "timestamp": now - 1000 * 60 * 60 * 24 * 120 },
                    { "weight": 97.9, "timestamp": now - 1000 * 60 * 60 * 24 * 150 },
                    { "weight": 95.3, "timestamp": now - 1000 * 60 * 60 * 24 * 250 },
                    { "weight": 99.9, "timestamp": now - 1000 * 60 * 60 * 24 * 400 },
                    { "weight": 95.8, "timestamp": now - 1000 * 60 * 60 * 24 * 420 }
                ]
            }
        }
    }