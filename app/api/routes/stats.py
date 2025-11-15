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
from uuid import uuid4
import numpy as np
import redis

from app.api.middleware.database import setup_connection, redis_connection
from app.api.middleware.auth_token import *
from app.api.routes.auth import verify_token
from app.api.middleware.misc import *
from app.api.routes.exercises import fetch_base_exercise_rows, fetch_variation_rows
from app.api.routes.muscles import get_muscle_maps
from app.api.routes.register import new_muscle_totals, new_workout_totals

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

        if row is None:
            row = await new_workout_totals(conn, credentials["user_id"])

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
        group_id_2_name_map = {
            row["group_id"]: row["group_name"] for row in muscle_rows
        }
        target_id_2_name_map = {
            row["target_id"]: row["target_name"] for row in muscle_rows
        }
        target_2_group_name_map = {
            row["target_name"]: row["group_name"] for row in muscle_rows
        }

        stats = []
        for workout_row in workout_rows:
            stats.append({
                "metadata": await stats_history_metadata(conn, workout_row, group_id_2_name_map),
                "workout_stats": await stats_history_workout(conn, workout_row),
                "workout_muscle_stats": await stats_history_workout_muscle(conn, workout_row, group_id_2_name_map, target_id_2_name_map, target_2_group_name_map),
                "replay": await stats_history_workout_replay(conn, workout_row)
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

async def stats_history_metadata(conn, workout_row, group_id_2_name_map):
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

    return {
        "started_at": date_to_timestamp_ms(workout_row["started_at"]),
        "duration": workout_row["duration_secs"],
        "top_groups": [group_id_2_name_map[row["muscle_group_id"]] for row in top_group_rows]
    }

async def stats_history_workout(conn, workout_row):
    prev_stats_row = await conn.fetchrow(
        """
        select *
        from previous_workout_stats
        where workout_id = $1
        """, workout_row["id"]
    )

    if prev_stats_row is None:
        return {
            "volume": 0,
            "num_sets": 0,
            "reps": 0,
            "num_exercises": 0
        }

    return {
        "volume": prev_stats_row["volume"],
        "num_sets": prev_stats_row["num_sets"],
        "reps": prev_stats_row["reps"],
        "num_exercises": prev_stats_row["num_exercises"]
    }

async def stats_history_workout_muscle(conn, workout_row, group_id_2_name_map, target_id_2_name_map, target_2_group_name_map):
    workout_muscle_stats = {}

    prev_group_stats_rows = await conn.fetch(
        """
        select *
        from previous_workout_muscle_group_stats 
        where workout_id = $1
        """, workout_row["id"]
    )
    for group_stats_row in prev_group_stats_rows:
        group_name = group_id_2_name_map[group_stats_row["muscle_group_id"]]
        workout_muscle_stats[group_name] = {
            "volume": group_stats_row["volume"],
            "num_sets": group_stats_row["num_sets"],
            "reps": group_stats_row["reps"],
            "targets": {}
        }

    for group_name in group_id_2_name_map.values():
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
        target_name = target_id_2_name_map[target_stats_row["muscle_target_id"]]
        group_name = target_2_group_name_map[target_name]
        workout_muscle_stats[group_name]["targets"][target_name] = {
            "volume": target_stats_row["volume"],
            "num_sets": target_stats_row["num_sets"],
            "reps": target_stats_row["reps"],
        }

    for target_name, group_name in target_2_group_name_map.items():
        if target_name in workout_muscle_stats[group_name]["targets"]: continue
        workout_muscle_stats[group_name]["targets"][target_name] = {
            "volume": 0,
            "num_sets": 0,
            "reps": 0,
        }

    for group_name in workout_muscle_stats:
        workout_muscle_stats[group_name]["targets"] = dict(sorted(workout_muscle_stats[group_name]["targets"].items()))

    workout_muscle_stats = dict(sorted(workout_muscle_stats.items()))
    return workout_muscle_stats

async def stats_history_workout_replay(conn, workout_row):
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
        set_data = []

        set_data_rows = await conn.fetch(
            """
            select *
            from workout_set_data
            where workout_exercise_id = $1
            order by order_index
            """, workout_exercise_row["id"]
        )
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
        if temp_row is None:
            exercise_name = "exercise not found"
            variation_name = None
        elif temp_row["parent_id"] is None:
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
            if exercise_name is None:
                exercise_name = "exercise not found"

        replay.append({
            "exercise_id": workout_exercise_row["id"],
            "exercise_name": exercise_name,
            "variation_name": variation_name,
            "set_data": set_data
        })

    return replay

# todo: fix Nonetype not subscriptable
@router.get("/stats/distributions")
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

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Uncaught exception")
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

@router.get("/stats/favourites")
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

@router.get("/stats/leaderboard/overall/{metric}")
async def stats_leaderboards_overall(
    top_num: int,
    side_num: int,
    num_rank_points: int,
    metric: overall_leaderboard_literal,
    credentials: dict = Depends(verify_token)
):
    try:
        conn = await setup_connection()
        r = await redis_connection()

        user_id = credentials["user_id"]
        zset = overall_leaderboard_zset(metric)
        if not zset_exists(r, zset):
            await resync_overall_zset(conn, r, zset, metric)

        return {
            "leaderboard": await leaderboard_data(
                conn, 
                r, 
                user_id, 
                zset, 
                top_num, 
                side_num, 
                num_rank_points
            )
        }

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Uncaught exception")
    finally:
        if conn: await conn.close()

async def resync_overall_zset(conn, r, zset, metric):
    await r.delete(zset)
    
    column = overall_column_map[metric]
    rows = await conn.fetch(
        """
        select user_id, $1
        from overall_leaderboard
        """, column
    )
    for row in rows:
        await r.zadd(zset, {
            row["user_id"]: row[column]
        })

@router.get("/stats/exercises-meta")
async def stats_exercises(credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()

        user_id = credentials["user_id"]
        exercises = {}
        exercise_rows = await fetch_base_exercise_rows(conn, user_id)
        for exercise_row in exercise_rows:
            variation_rows = await fetch_variation_rows(conn, user_id, exercise_row["id"])
            variations = {
                variation_row["id"]: variation_row["name"]
                for variation_row in variation_rows
            } 
            exercises[exercise_row["id"]] = {
                "name": exercise_row["name"],
                "variations": variations
            }

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

@router.get("/stats/leaderboard/exercise/{exercise_id}/{metric}")
async def stats_leaderboards_overall(
    top_num: int,
    side_num: int,
    num_rank_points: int,
    exercise_id: str,
    metric: exercise_leaderboard_literal,
    credentials: dict = Depends(verify_token)
):
    try:
        conn = await setup_connection()
        r = await redis_connection()

        user_id = credentials["user_id"]
        zset = exercise_leaderboard_zset(exercise_id, metric)
        if not zset_exists(r, zset):
            await resync_exercise_zset(conn, r, zset, exercise_id, metric)

        return {
            "leaderboard": await leaderboard_data(
                conn, 
                r, 
                user_id, 
                zset, 
                top_num, 
                side_num, 
                num_rank_points
            )
        }

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Uncaught exception")
    finally:
        if conn: await conn.close()

async def resync_exercise_zset(conn, r, zset, exercise_id, metric):
    await r.delete(zset)
    
    column = exercise_column_map[metric]
    rows = await conn.fetch(
        """
        select user_id, $1
        from exercise_leaderboard
        where exercise_id = $2
        """, column, exercise_id
    )
    for row in rows:
        await r.zadd(zset, {
            row["user_id"]: row[column]
        })

async def zset_exists(r, zset_key) -> bool:
    return await r.exists(zset_key)

async def leaderboard_data(conn, r, user_id, zset, top_num, side_num, num_rank_points):
    count = await r.zcard(zset)
    max_rank = count - 1

    user_rank = await r.zrevrank(zset, user_id)

    if user_rank == None or user_rank <= top_num + side_num:
        fracture = None
        top = await r.zrevrange(zset, 0, top_num + 2 * side_num, withscores=True)
        leaderboard = await leaderboard_items(conn, top, 0)
    elif user_rank >= count - side_num - 1:
        fracture = top_num
        top = await r.zrevrange(zset, 0, top_num - 1, withscores=True)
        top_ranks =  await leaderboard_items(conn, top, 0)
        sides = await r.zrevrange(zset, max_rank - 2 * side_num, max_rank, withscores=True)
        side_ranks = await leaderboard_items(conn, sides, user_rank - side_num)
        leaderboard = top_ranks + side_ranks
    else:
        fracture = top_num
        top = await r.zrevrange(zset, 0, top_num - 1, withscores=True)
        top_ranks =  await leaderboard_items(conn, top, 0)
        sides = await r.zrevrange(zset, user_rank - side_num, user_rank + side_num, withscores=True)
        side_ranks = await leaderboard_items(conn, sides, user_rank - side_num)
        leaderboard = top_ranks + side_ranks

    adjusted_user_rank = user_rank + 1 if user_rank != None else None
    return {
        "fracture": fracture,
        "leaderboard": leaderboard,
        "user_rank": adjusted_user_rank,
        "max_rank": max_rank + 1,
        "friend_ids": [],
        "rank_data": await fetch_rank_data(r, user_id, zset, num_rank_points)
    }

async def leaderboard_items(conn, items, start_rank):
    leaderboard = []
    for i, items in enumerate(items):
        username = await conn.fetchval(
            """
            select username
            from users
            where id = $1
            """, items[0]
        ),
        leaderboard.append({
            "user_id": items[0],
            "username": username if username else "",
            "rank": i + start_rank,
            "value": items[1]
        })
    return leaderboard

async def fetch_rank_data(r, user_id, zset, num_rank_points):
    rank_data = []
    user_value = None
    for item in await r.zrange(zset, 0, -1, withscores=True):
        rank_data.append({
            "user_id": item[0],
            "value": item[1],
            "showVerticalLine": True if item[0] == user_id else False
        })
        if item[0] == user_id:
            user_value = item[1]

    if len(rank_data) <= num_rank_points: return rank_data

    rank_data = random.sample(rank_data, 50)
    if user_value is None: return rank_data

    for item in rank_data:
        if item["user_id"] != user_id: continue
        break
    else:
        rank_data.append({
            "user_id": user_id,
            "value": user_value,
            "showVerticalLine": True
        })
        rank_data = sorted(rank_data, lambda e: e["value"])

    return rank_data