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

        muscle_rows = await conn.fetch(
            """
            select group_id, group_name, target_id, target_name
            from muscle_groups_targets
            """
        )
        group_id_name_map = {
            row["group_id"]: row["group_name"] for row in muscle_rows
        }

        target_id_name_map = {
            row["target_id"]: row["target_name"] for row in muscle_rows
        }

        target_group_map = {
            row["target_name"]: row["group_name"] for row in muscle_rows
        }

        stats = []
        for workout_row in workout_rows:
            top_group_rows = await conn.fetch(
                """
                select *
                from previous_workout_muscle_group_stats
                where workout_id = $1
                order by volume desc
                limit 3
                """, workout_row["id"]
            )
            
            metadata = {
                "started_at": date_to_timestamp_ms(workout_row["started_at"]),
                "duration": workout_row["duration_secs"],
                "top_groups": [group_id_name_map[row["muscle_group_id"]] for row in top_group_rows]
            }

            prev_stats_row = await conn.fetchrow(
                """
                select *
                from previous_workout_stats
                where workout_id = $1
                """, workout_row["id"]
            )

            workout_stats = {
                "volume": prev_stats_row["volume"],
                "num_sets": prev_stats_row["num_sets"],
                "reps": prev_stats_row["reps"],
            }

            workout_muscle_stats = {}

            prev_group_stats_rows = await conn.fetch(
                """
                select *
                from previous_workout_muscle_group_stats 
                where workout_id = $1
                """, workout_row["id"]
            )
            for group_stats_row in prev_group_stats_rows:
                group_name = group_id_name_map[group_stats_row["muscle_group_id"]]
                workout_muscle_stats[group_name] = {
                    "volume": group_stats_row["volume"],
                    "num_sets": group_stats_row["num_sets"],
                    "reps": group_stats_row["reps"],
                    "targets": {}
                }

            prev_target_stats_rows = await conn.fetch(
                """
                select *
                from previous_workout_muscle_target_stats 
                where workout_id = $1
                """, workout_row["id"]
            )
            for target_stats_row in prev_target_stats_rows:
                target_name = target_id_name_map[target_stats_row["muscle_target_id"]]
                group_name = target_group_map[target_name]
                workout_muscle_stats[group_name]["targets"][target_name] = {
                    "volume": target_stats_row["volume"],
                    "num_sets": target_stats_row["num_sets"],
                    "reps": target_stats_row["reps"],
                }

            replay = []
            workout_exercise_rows = await conn.fetch(
                """
                select *
                from workout_exercises
                where workout_id = $1
                order by order_index
                """, workout_row["id"]
            )
            for workout_exercise_row in workout_exercise_rows:
                set_data_rows = await conn.fetch(
                    """
                    select *
                    from workout_set_data
                    where workout_exercise_id = $1
                    order by order_index
                    """, workout_exercise_row["id"]
                )
                set_data = []
                for set_data_row in set_data_rows:
                    set_data.append({
                        "reps": set_data_row["reps"],
                        "weight": set_data_row["weight"],
                        "num_sets": set_data_row["num_sets"],
                        "set_class": set_data_row["set_class"],
                    })

                temp_row = await conn.fetchrow(
                    """
                    select *
                    from exercises
                    where id = $1
                    """, workout_exercise_row["exercise_id"]
                )
                if temp_row["parent_id"] is None:
                    exercise_name = temp_row["name"]
                    variation_name = None
                else:
                    variation_name = temp_row["name"]
                    exercise_name = await conn.fetchval(
                        """
                        select name
                        from exercises
                        where id = $1
                        """, temp_row["parent_id"]
                    )

                replay.append({
                    "exercise_id": workout_exercise_row["id"],
                    "exercise_name": exercise_name,
                    "variation_name": variation_name,
                    "set_data": set_data
                })


            stats.append({
                "metadata": metadata,
                "workout_stats": workout_stats,
                "workout_muscle_stats": workout_muscle_stats,
                "replay": replay
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
