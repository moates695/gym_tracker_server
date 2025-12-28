from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from fastapi.security import HTTPBearer

from app.api.middleware.database import setup_connection
from app.api.middleware.auth_token import *
from app.api.routes.auth import verify_token
from app.api.middleware.misc import *

router = APIRouter()
security = HTTPBearer()

@router.get("/list/all")
async def exercises_list_all(credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()

        user_id = credentials["user_id"]
        exercise_rows = await fetch_base_exercise_rows(conn, user_id)

        exercises = []
        for exercise_row in exercise_rows:
            exercise_id = str(exercise_row["id"])
            variation_rows = await fetch_variation_rows(conn, user_id, exercise_row["id"])

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
                    "frequency": await fetch_exercise_frequency(conn, variation_row["id"], user_id),
                })
                if variation_row["is_body_weight"]:
                    variations[-1]["ratios"] = await fetch_bodyweight_ratios(conn, str(variation_row["id"]))

            exercises.append({
                "id": exercise_id,
                "name": exercise_row["name"],
                "is_body_weight": exercise_row["is_body_weight"],
                "muscle_data": await fetch_exercise_muscle_data(conn, exercise_row),
                "description": exercise_row["description"],
                "weight_type": exercise_row["weight_type"],
                "is_custom": exercise_row["is_custom"],
                "frequency": await fetch_exercise_frequency(conn, exercise_row["id"], user_id),
                "variations": variations
            })
            if exercise_row["is_body_weight"]:
                exercises[-1]["ratios"] = await fetch_bodyweight_ratios(conn, exercise_id)

        exercises.sort(key=lambda e: e["name"].lower())

        return {
            "exercises": exercises
        }

    except SafeError as e:
        raise e
    except Exception as e:
        print(str(e))
        raise Exception('uncaught error')
    finally:
        if conn: await conn.close()

async def fetch_base_exercise_rows(conn, user_id):
    return await conn.fetch(
        """
        select *, (user_id = $1) as is_custom
        from exercises
        where (
            user_id is null
            or user_id = $1
        )
        and parent_id is null
        order by name
        """, user_id
    )

async def fetch_variation_rows(conn, user_id, parent_id):
    return await conn.fetch(
        """
        select *, (user_id = $1) as is_custom
        from exercises
        where (
            user_id is null
            or user_id = $1
        )
        and parent_id = $2
        order by name
        """, user_id, parent_id
    )

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

async def fetch_exercise_frequency(conn, exercise_id, user_id):
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