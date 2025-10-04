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
import math

from app.api.middleware.database import setup_connection
from app.api.middleware.auth_token import *
from app.api.routes.auth import verify_token
from app.api.middleware.misc import *
from app.api.routes.muscles import get_muscle_maps

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
                and volume <> 0
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
                "num_exercises": prev_stats_row["num_exercises"]
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

            for group_name in group_id_name_map.values():
                if group_name in workout_muscle_stats: continue
                workout_muscle_stats[group_name] = {
                    "volume": 0,
                    "num_sets": 0,
                    "reps": 0,
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

            for target_name, group_name in target_group_map.items():
                if target_name in workout_muscle_stats[group_name]["targets"]: continue
                workout_muscle_stats[group_name]["targets"][target_name] = {
                    "volume": 0,
                    "num_sets": 0,
                    "reps": 0,
                }

            for group_name in workout_muscle_stats:
                workout_muscle_stats[group_name]["targets"] = dict(sorted(workout_muscle_stats[group_name]["targets"].items()))

            workout_muscle_stats = dict(sorted(workout_muscle_stats.items()))

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
                        "class": set_data_row["set_class"],
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

@router.get("/stats/distributions")
async def stats_distributions(credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()

        distributions = {}
        muscle_maps = await get_muscle_maps()
        
        group_rows = await conn.fetch(
            """
            select t.*, m.name
            from workout_muscle_group_totals t
            inner join muscle_groups m
            on t.muscle_group_id = m.id
            where t.user_id = $1
            """, credentials["user_id"]
        )

        for group_row in group_rows:
            targets = {}
            for target_name in muscle_maps["group_to_targets"][group_row["name"]]:
                target_row = await conn.fetchrow(
                    """
                    select t.*
                    from workout_muscle_target_totals t
                    inner join muscle_targets m
                    on t.muscle_target_id = m.id
                    where user_id = $1
                    and m.name = $2
                    """, credentials["user_id"], target_name
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

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Uncaught exception")
    finally:
        if conn: await conn.close()

@router.get("/stats/favourites")
async def stats_favourites(credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()

        total_rows = await conn.fetch(
            """
            select *
            from exercise_totals
            where user_id = $1
            """, credentials["user_id"]
        )

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

        data = []
        for total_row in total_rows:
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

# return top X people, then surrounding Y people from table?
@router.get("/stats/leaderboards/overall/volume")
async def stats_leaderboards_overall_volume(top_num: int, side_num: int, credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()

        user_row_num = await conn.fetchval(
            """
            with numbered as (
                select
                    *,
                    row_number() over (order by volume desc) as row_num
                from volume_leaderboard
            )
            select n.row_num
            from numbered n
            inner join volume_leaderboard l
            on n.user_id = l.user_id
            where l.user_id = $1
            """, credentials["user_id"]
        )
        num_rows = await conn.fetchval(
            """
            select count(*)
            from volume_leaderboard
            """
        )

        fracture = None
        if user_row_num <= top_num + side_num + 1:
            rows = await conn.fetch(
                """
                select 
                    l.*,
                    rank() over (order by volume desc) rank_num,
                    u.username
                from volume_leaderboard l
                inner join users u
                on l.user_id = u.id
                order by volume desc
                limit $1
                """, top_num + 2 * side_num + 1
            )
            leaderboard = []
            for row in rows:
                leaderboard.append({
                    "username": row["username"],
                    "volume": row["volume"],
                    "rank": row["rank_num"],
                })
        elif user_row_num >= num_rows - side_num:
            fracture = top_num
            top_rows = await conn.fetch(
                """
                select 
                    l.*,
                    rank() over (order by volume desc) rank_num,
                    u.username
                from volume_leaderboard l
                inner join users u
                on l.user_id = u.id
                order by l.volume desc
                limit $1
                """, top_num
            )

            side_rows = await conn.fetch(
                """
                with numbered as (
                    select
                        *,
                        row_number() over (order by volume desc) as row_num,
                        rank() over (order by volume desc) as rank_num
                    from volume_leaderboard
                )
                select n.*, u.username
                from numbered n
                inner join users u
                on n.user_id = u.id
                where n.row_num >= $1
                order by n.row_num
                """, num_rows - 2 * side_num
            )

            leaderboard = []
            for row in top_rows + side_rows:
                leaderboard.append({
                    "username": row["username"],
                    "volume": row["volume"],
                    "rank": row["rank_num"],
                })
        else:
            fracture = top_num
            top_rows = await conn.fetch(
                """
                select 
                    l.*,
                    rank() over (order by volume desc) rank_num,
                    u.username
                from volume_leaderboard l
                inner join users u
                on l.user_id = u.id
                order by l.volume desc
                limit $1
                """, top_num
            )

            side_rows = await conn.fetch(
                """
                with numbered as (
                    select
                        *,
                        row_number() over (order by volume desc) as row_num,
                        rank() over (order by volume desc) as rank_num
                    from volume_leaderboard
                )
                select n.*, u.username
                from numbered n
                inner join users u
                on n.user_id = u.id
                where n.row_num between $1 and $2
                order by n.row_num
                """, user_row_num - side_num, user_row_num + side_num
            )

            leaderboard = []
            for row in top_rows + side_rows:
                leaderboard.append({
                    "username": row["username"],
                    "volume": row["volume"],
                    "rank": row["rank_num"],
                })

        return {
            "leaderboard": leaderboard,
            "fracture": fracture
        }

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Uncaught exception")
    finally:
        if conn: await conn.close()

# overall most volume, sets, reps, workouts, duration, excercises
#   filter based on gender and current age (new date of birth input field)
# for each exercise
#   most volume, sets, reps
#       filter gender, age
#   n rep max
#       filter by gender, age at time of lift, weight at time of lift, height at time of lift

# give top percentage and total rank based on filters

# age, height filter should be a range
# show global leaderboards and then versus friends

# on FE show a bell curve based on chosen stats?

#! use insert on conflict for updates?
#! refresh materialised views (or may need to drop because of filtering)