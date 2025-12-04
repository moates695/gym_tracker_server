from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer

from app.api.middleware.database import setup_connection
from app.api.middleware.auth_token import *
from app.api.routes.auth import verify_token
from app.api.middleware.misc import *
from app.api.routes.register.register import new_workout_totals

router = APIRouter()
security = HTTPBearer()

@router.get("/workout_totals") 
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

        if row is None:
            row = await new_workout_totals(conn, credentials["user_id"])

        return {
            "totals": {
                "volume": row["volume"],
                "num_sets": row["num_sets"],
                "reps": row["reps"],
                "duration": row["duration"] / 60,
                "num_workouts": row["num_workouts"],
                "num_exercises": row["num_exercises"],
            }
        }

    except SafeError as e:
        raise e
    except Exception as e:
        print(str(e))
        raise Exception('uncaught error')
    finally:
        if conn: await conn.close()