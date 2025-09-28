from fastapi import APIRouter, HTTPException, Security, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import List, Literal
import jwt
import os
from datetime import datetime, timedelta, timezone
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import random
import json
from copy import deepcopy

from app.api.middleware.database import setup_connection
from app.api.middleware.auth_token import *
from app.api.routes.auth import verify_token
from app.api.middleware.misc import *

router = APIRouter()
security = HTTPBearer()

@router.get("/stats/workout_totals") 
async def stats_workout_totals(credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()

        row = await conn.fetchrow(
            """
            select *
            from workout_totals
            where user_id = $1
            """, credentials["user_id"]
        )

        if row is None: return {
            "totals": None
        }

        return {
            "totals": {
                "volume": row["volume"],
                "num_sets": row["num_sets"],
                "reps": row["reps"],
                "duration": row["duration"],
                "num_workouts": row["num_workouts"],
                "num_exercises": row["num_exercises"],
            }
        }

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Uncaught exception")
    finally:
        if conn: await conn.close()

@router.get("/stats/history")
async def stats_history(credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()

        workout_rows = await conn.fetch(
            """
            select *
            from workouts
            where user_id = $1
            order by started_at desc
            """, credentials["user_id"]
        )
        if workout_rows is None: workout_rows = []

        stats = []
        for workout_row in workout_rows:
            metadata = {
                "started_at": date_to_timestamp_ms(workout_row["started_at"]),
                "duration": workout_row["duration_secs"]
            }

            prev_stats_row = await conn.fetchrow(
                """
                select *
                from previous_workout_stats
                where workout_id = $1
                """, workout_row["id"]
            )

            prev_stats = {
                "volume": prev_stats_row["volume"],
                "num_sets": prev_stats_row["num_sets"],
                "reps": prev_stats_row["reps"],
            }

            # prev_muscle_stats_row = await conn.fetchrow(
            #     """
            #     select *
            #     from previous_workout_stats
            #     where workout_id = $1
            #     """, workout_row["id"]
            # )

            prev_group_stats = {}
            prev_target_stats = {}



            stats.append({
                "metadata": metadata,
                "prev_stats": prev_stats,
                "prev_group_stats": prev_group_stats,
                "prev_target_stats": prev_target_stats,
            })

        return {
            "stats": stats
        }

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Uncaught exception")
    finally:
        if conn: await conn.close()
