from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from datetime import datetime, timezone, timedelta
from fastapi.security import HTTPBearer
from copy import deepcopy
import math

from app.api.middleware.database import setup_connection
from app.api.middleware.auth_token import *
from app.api.routes.auth import verify_token
from app.api.middleware.misc import *

router = APIRouter()
security = HTTPBearer()

@router.get("/muscles-history")
async def exercise_history(credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()

        rows = await conn.fetch(
            """
            select w.started_at, we.exercise_id, wsd.reps, wsd.weight, wsd.num_sets, mgt.group_name, mgt.target_name, emt.ratio
            from workouts w
            inner join workout_exercises we
            on we.workout_id = w.id
            inner join workout_set_data wsd
            on wsd.workout_exercise_id = we.id
            inner join exercise_muscle_targets emt
            on emt.exercise_id = we.exercise_id
            inner join muscle_groups_targets mgt
            on mgt.target_id = emt.muscle_target_id
            where w.user_id = $1
            """,
            credentials["user_id"],
            # datetime.now(tz=timezone.utc) - timedelta(days=365)
        )

        empty = {
            "volume": 0,
            "sets": 0,
            "reps": 0,
        }

        timespans = {
            "week": timedelta(weeks=1),
            "month": timedelta(days=30),
            "3_months": timedelta(days=30) * 3,
            "6_months": timedelta(days=30) * 6,
            "year": timedelta(days=365),
        }
        utc_now = datetime.now(tz=timezone.utc)

        added_exercise_groups = {}

        data = {}
        for row in rows:
            spans = []
            for key, delta in timespans.items():
                spans.append(key)
                if row["started_at"] >= utc_now - delta: break
            else:
                spans.append("all")

            volume = row["reps"] * row["weight"] * row["num_sets"]

            group = row["group_name"]
            if group not in data:
                data[group] = deepcopy(empty) | {
                    "targets": {}
                }

            exercise_id = row["exercise_id"]
            if exercise_id not in added_exercise_groups:
                added_exercise_groups[exercise_id] = []

            if group not in added_exercise_groups[exercise_id]:
                data[group]["volume"] += volume
                data[group]["sets"] += row["num_sets"]
                data[group]["reps"] += row["reps"]
                added_exercise_groups[exercise_id] = group

            target = row["target_name"]
            if target not in data[group]["targets"]:
                data[group]["targets"][target] = deepcopy(empty)

            data[group]["targets"][target]["volume"] += volume
            data[group]["targets"][target]["sets"] += row["num_sets"]
            data[group]["targets"][target]["reps"] += row["reps"]
            
        return {
            "data": data
        }

    except SafeError as e:
        raise e
    except Exception as e:
        print(str(e))
        raise Exception('uncaught error')
    finally:
        if conn: await conn.close()