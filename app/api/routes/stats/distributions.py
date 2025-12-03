from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer

from app.api.middleware.database import setup_connection
from app.api.middleware.auth_token import *
from app.api.routes.auth import verify_token
from app.api.middleware.misc import *
from app.api.routes.muscles import get_muscle_maps
from app.api.routes.register.register import new_muscle_totals

router = APIRouter()
security = HTTPBearer()

@router.get("/distributions")
async def stats_distributions(credentials: dict = Depends(verify_token)):
    user_id = credentials["user_id"]
    try:
        conn = await setup_connection()

        distributions = {}
        muscle_maps = await get_muscle_maps()

        group_rows = await fetch_workout_muscle_group_rows(conn, user_id)

        if group_rows is None:
            await new_muscle_totals(conn, user_id)
            group_rows = await fetch_workout_muscle_group_rows(conn, user_id)

        for group_row in group_rows:
            targets = {}
            for target_name in muscle_maps["group_to_targets"][group_row["name"]]:
                target_row = await conn.fetchrow(
                    """
                    select t.*
                    from workout_muscle_target_totals t
                    inner join muscle_targets m
                    on t.muscle_target_id = m.id
                    where t.user_id = $1
                    and m.name = $2
                    """, user_id, target_name
                )
                if target_row is None:
                    target_id = await conn.fetchval(
                        """
                        select id
                        from muscle_targets
                        where name = $1
                        """, target_name
                    )
                    target_row = await conn.fetchrow(
                        """
                        insert into workout_muscle_target_totals
                        (user_id, muscle_target_id, volume, num_sets, reps, counter)
                        values
                        ($1, $2, 0.0, 0, 0, 0)
                        returning *
                        """, user_id, target_id
                    )

                targets[target_name] = {
                    "volume": target_row["volume"],
                    "num_sets": target_row["num_sets"],
                    "reps": target_row["reps"],
                    "num_exercises": target_row["counter"],
                }
            targets = dict(sorted(targets.items()))

            distributions[group_row["name"]] = {
                "volume": group_row["volume"],
                "num_sets": group_row["num_sets"],
                "reps": group_row["reps"],
                "num_exercises": group_row["counter"],
                "targets": targets
            }

        return {
            "distributions": dict(sorted(distributions.items()))
        }

    except SafeError as e:
        raise e
    except Exception as e:
        print(str(e))
        raise Exception('uncaught error')
    finally:
        if conn: await conn.close()

async def fetch_workout_muscle_group_rows(conn, user_id):
    return await conn.fetch(
        """
        select t.*, m.name
        from workout_muscle_group_totals t
        inner join muscle_groups m
        on t.muscle_group_id = m.id
        where t.user_id = $1
        """, user_id
    )