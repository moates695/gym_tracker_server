from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer

from app.api.middleware.database import setup_connection
from app.api.middleware.auth_token import *
from app.api.routes.auth import verify_token
from app.api.middleware.misc import *

router = APIRouter()
security = HTTPBearer()

@router.get("/favourites")
async def stats_favourites(credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()

        exercise_name_rows = await conn.fetch(
            """
            select *
            from exercise_base_variants
            """
        )
        name_map = {}
        for row in exercise_name_rows:
            name_map[str(row["base_id"])] = {
                "exercise_name": row["base_name"],
                "variation_name": None
            }
            if row["variant_id"] is None: continue
            name_map[str(row["variant_id"])] = {
                "exercise_name": row["base_name"],
                "variation_name": row["variant_name"]
            }

        total_rows = await conn.fetch(
            """
            select *
            from exercise_totals
            where user_id = $1
            """, credentials["user_id"]
        )

        data = []
        for total_row in total_rows:
            try:
                exercise_id = str(total_row["exercise_id"])
                data.append({
                    "exercise_id": exercise_id,
                    "exercise_name": name_map[exercise_id]["exercise_name"],
                    "volume": total_row["volume"],
                    "num_sets": total_row["num_sets"],
                    "reps": total_row["reps"],
                    "counter": total_row["counter"],
                    "groups": await getExerciseGroups(conn, exercise_id)
                })
                variation_name = name_map[exercise_id]["variation_name"]
                if variation_name is None: continue
                data[-1]["variation_name"] = variation_name
            except Exception as e:
                continue

        return {
            "favourites": data
        }

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Uncaught exception")
    finally:
        if conn: await conn.close()

async def getExerciseGroups(conn, exercise_id):
    rows = await conn.fetch(
        """
        select distinct mgt.group_name
        from exercise_muscle_targets emt
        inner join muscle_groups_targets mgt 
        on emt.muscle_target_id = mgt.target_id 
        where emt.exercise_id = $1
        and emt.ratio >= 7
        """, exercise_id
    )

    return [row["group_name"] for row in rows]