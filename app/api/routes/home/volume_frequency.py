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
from app.api.routes.exercises.list_all import get_days_past
from app.api.routes.muscles import get_muscle_maps

router = APIRouter()
security = HTTPBearer()

@router.get("/volume-frequency")
async def volume_frequency(credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()
        
        rows = await conn.fetch(
            """
            select w.started_at, pws.volume
            from workouts w
            inner join previous_workout_stats pws
            on pws.workout_id = w.id
            where w.user_id = $1
            and w.started_at >= now() - interval '28 days'
            """, credentials["user_id"]
        )
        
        days_past_volume = {}
        for history_row in rows:
            days_past = get_days_past(history_row["started_at"])
            if days_past == 0 or days_past > 28: continue
            
            if days_past not in days_past_volume.keys():
                days_past_volume[days_past] = 0
            days_past_volume[days_past] += history_row["volume"]

        return {
            "frequency": days_past_volume
        }

    except SafeError as e:
        raise e
    except Exception as e:
        print(str(e))
        raise Exception('uncaught error')
    finally:
        if conn: await conn.close()