from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
import random

from app.api.middleware.database import setup_connection, redis_connection
from app.api.middleware.auth_token import *
from app.api.routes.auth import verify_token
from app.api.middleware.misc import *
from app.api.routes.exercises.list_all import fetch_base_exercise_rows, fetch_variation_rows

router = APIRouter()
security = HTTPBearer()

@router.get("/leaderboard/overall/{metric}")
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
        zset = overall_zset_name(metric)
        if not await zset_exists(r, zset):
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

@router.get("/exercises-meta")
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

@router.get("/leaderboard/exercise/{exercise_id}/{metric}")
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
        zset = exercise_zset_name(exercise_id, metric)
        if not await zset_exists(r, zset):
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
            "rank": i + start_rank + 1,
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