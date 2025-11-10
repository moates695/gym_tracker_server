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
import traceback

from app.api.middleware.database import setup_connection, redis_connection
from app.api.middleware.auth_token import *
from app.api.routes.auth import verify_token
from app.api.middleware.misc import *

router = APIRouter()
security = HTTPBearer()

class SetData(BaseModel):
    reps: int
    weight: float | None
    num_sets: int
    set_class: Literal['working', 'dropset', 'warmup', 'cooldown']

class Exercise(BaseModel):
    id: str
    set_data: List[SetData]

class WorkoutSave(BaseModel):
    exercises: List[Exercise]
    start_time: int #? timestamp ms
    duration: int #? ms

#? bodyweight determined on the client
@router.post("/workout/save") 
async def workout_save(req: WorkoutSave, credentials: dict = Depends(verify_token)):
    try:
        user_id = credentials["user_id"]

        conn = None
        if len(req.exercises) == 0: return

        conn = await setup_connection()
        tx = conn.transaction()
        await tx.start()

        start_time = datetime.fromtimestamp(req.start_time / 1000, tz=timezone.utc)
        workout_id = await conn.fetchval(
            """
            insert into workouts
            (user_id, started_at, duration_secs)
            values
            ($1, $2, $3)
            returning id;
            """, user_id, start_time, req.duration / 1000
        )

        totals = {
            "volume": 0,
            "num_sets": 0,
            "reps": 0,
        }
        group_totals = {}
        target_totals = {}

        for i, exercise in enumerate(req.exercises):
            await save_exercise(conn, workout_id, exercise, i)
            await process_exercise(conn, user_id, exercise, totals, group_totals, target_totals)

        await update_workout_totals(conn, user_id, totals, req)
        await update_muscle_totals(conn, user_id, group_totals, target_totals)
        await update_previous_stats(conn, workout_id, totals, group_totals, target_totals, req)
        await update_leaderboards(conn, user_id, totals)

        await tx.commit()
    except HTTPException as e:
        await tx.rollback()
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        await tx.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Uncaught exception")
    finally:
        if conn: await conn.close()
    return {}

async def save_exercise(conn, workout_id, exercise: Exercise, index): 
    workout_exercise_id = await conn.fetchval(
        """
        insert into workout_exercises
        (workout_id, exercise_id, order_index)
        values
        ($1, $2, $3)
        returning id
        """, workout_id, exercise.id, index
    )

    for j, set_data in enumerate(exercise.set_data):
        await save_set_data(conn, workout_exercise_id, set_data, j)

async def save_set_data(conn, workout_exercise_id, set_data: SetData, index):
    await conn.execute(
        """
        insert into workout_set_data
        (workout_exercise_id, order_index, reps, weight, num_sets, set_class)
        values
        ($1, $2, $3, $4, $5, $6)
        """, workout_exercise_id, index, set_data.reps, set_data.weight, set_data.num_sets, set_data.set_class
    )

async def process_exercise(conn, user_id, exercise: Exercise, totals, group_totals, target_totals):
    group_rows = await conn.fetch(
        """
        select distinct on (group_id) ratio, group_id
        from exercise_muscle_data
        where exercise_id = $1
        order by group_id, ratio desc
        """, exercise.id
    )

    target_rows = await conn.fetch(
        """
        select ratio, target_id
        from exercise_muscle_data
        where exercise_id = $1
        """, exercise.id
    )

    exercise_totals = {
        "volume": 0,
        "num_sets": 0,
        "reps": 0,
    }

    for set_data in exercise.set_data:
        process_exercise_sets(set_data, totals, exercise_totals, group_rows, group_totals, target_rows, target_totals)

    for group_row in group_rows:
        group_totals[group_row["group_id"]]["counter"] += 1

    for target_row in target_rows:
        target_totals[target_row["target_id"]]["counter"] += 1

    current_exercise_totals = await conn.fetchrow(
        """
        select *
        from exercise_totals
        where user_id = $1
        and exercise_id = $2
        """, user_id, exercise.id
    )
    if current_exercise_totals is None:
        current_exercise_totals = await conn.fetchrow(
            """
            insert into exercise_totals
            (user_id, exercise_id, volume, num_sets, reps, counter)
            values
            ($1, $2, 0.0, 0, 0, 0)
            returning *
            """, user_id, exercise.id
        )
    
    await conn.execute(
        """
        update exercise_totals
        set 
            volume = $1,
            num_sets = $2,
            reps = $3,
            counter = $4
        where user_id = $5
        and exercise_id = $6
        """,
        current_exercise_totals["volume"] + exercise_totals["volume"],
        current_exercise_totals["num_sets"] + exercise_totals["num_sets"],
        current_exercise_totals["reps"] + exercise_totals["reps"],
        current_exercise_totals["counter"] + 1,
        user_id,
        exercise.id
    )

def process_exercise_sets(set_data, totals, exercise_totals, group_rows, group_totals, target_rows, target_totals):
    empty_totals = {
        "volume": 0,
        "num_sets": 0,
        "reps": 0,
        "counter": 0
    }

    volume = set_data.reps * set_data.weight * set_data.num_sets

    totals["volume"] += volume
    totals["num_sets"] += set_data.num_sets
    totals["reps"] += set_data.reps

    exercise_totals["volume"] += volume
    exercise_totals["num_sets"] += set_data.num_sets
    exercise_totals["reps"] += set_data.reps

    for group_row in group_rows:
        if group_row["group_id"] not in group_totals:
            group_totals[group_row["group_id"]] = deepcopy(empty_totals)
        group_totals[group_row["group_id"]]["volume"] += (group_row["ratio"] / 10) * volume
        group_totals[group_row["group_id"]]["num_sets"] += set_data.num_sets
        group_totals[group_row["group_id"]]["reps"] += set_data.reps

    for target_row in target_rows:
        if target_row["target_id"] not in target_totals:
            target_totals[target_row["target_id"]] = deepcopy(empty_totals)
        target_totals[target_row["target_id"]]["volume"] += (target_row["ratio"] / 10) * volume
        target_totals[target_row["target_id"]]["num_sets"] += set_data.num_sets
        target_totals[target_row["target_id"]]["reps"] += set_data.reps

async def update_workout_totals(conn, user_id, totals, req):
    current_totals = await conn.fetchrow(
        """
        select *
        from workout_totals
        where user_id = $1
        """, user_id
    )

    if current_totals == None:
        current_totals = await conn.fetch(
            """
            insert into workout_totals
            (user_id, volume, num_sets, reps, duration, num_workouts, num_exercises)
            values
            ($1, 0.0, 0, 0, 0.0, 0, 0)
            returning *
            """, user_id
        )

    await conn.execute(
        """
        update workout_totals
        set
            volume = $1,
            num_sets = $2,
            reps = $3,
            duration = $4,
            num_workouts = $5,
            num_exercises = $6
        where user_id = $7
        """, 
        current_totals["volume"] + totals["volume"],
        current_totals["num_sets"] + totals["num_sets"],
        current_totals["reps"] + totals["reps"],
        current_totals["duration"] + req.duration / 1000,
        current_totals["num_workouts"] + 1,
        current_totals["num_exercises"] + len(req.exercises),
        user_id
    )

async def update_muscle_totals(conn, user_id, group_totals, target_totals):
    for key in ["group", "target"]:
        muscle_totals = group_totals if key == "group" else target_totals
        for muscle_id, muscle_total in muscle_totals.items():
            current_muscle_totals = await conn.fetchrow(
                f"""
                select *
                from workout_muscle_{key}_totals
                where user_id = $1
                and muscle_{key}_id = $2
                """, user_id, muscle_id
            )

            if current_muscle_totals == None:
                current_muscle_totals = await conn.fetch(
                    f"""
                    insert into workout_muscle_{key}_totals
                    (user_id, volume, num_sets, reps, counter)
                    values
                    ($1, $2, 0.0, 0, 0, 0)
                    returning *
                    """, user_id, muscle_id
                )

            await conn.execute(
                f"""
                update workout_muscle_{key}_totals
                set
                    volume = $1,
                    num_sets = $2,
                    reps = $3,
                    counter = $4
                where user_id = $5
                and muscle_{key}_id = $6
                """,
                current_muscle_totals["volume"] + muscle_total["volume"],
                current_muscle_totals["num_sets"] + muscle_total["num_sets"],
                current_muscle_totals["reps"] + muscle_total["reps"],
                current_muscle_totals["counter"] + muscle_total["counter"],
                user_id,
                muscle_id
            )

async def update_previous_stats(conn, workout_id, totals, group_totals, target_totals, req: WorkoutSave):
    await conn.execute(
        """
        insert into previous_workout_stats
        (workout_id, volume, num_sets, reps, num_exercises)
        values
        ($1, $2, $3, $4, $5)
        """, workout_id, totals["volume"], totals["num_sets"], totals["reps"], len(req.exercises)
    )

    for group_id, group_total in group_totals.items():
        await conn.execute(
            """
            insert into previous_workout_muscle_group_stats
            (workout_id, muscle_group_id, volume, num_sets, reps)
            values
            ($1, $2, $3, $4, $5)
            """, workout_id, group_id, group_total["volume"], group_total["num_sets"], group_total["reps"]
        )

    for target_id, target_total in target_totals.items():
        await conn.execute(
            """
            insert into previous_workout_muscle_target_stats
            (workout_id, muscle_target_id, volume, num_sets, reps)
            values
            ($1, $2, $3, $4, $5)
            """, workout_id, target_id, target_total["volume"], target_total["num_sets"], target_total["reps"]
        )

async def update_leaderboards(conn, user_id, totals, req: WorkoutSave):
    current = await conn.fetchrow(
        """
        select *
        from overall_leaderboard
        where user_id = $1
        """, user_id
    )

    if current is None:
        current = await conn.fetch(
            """
            insert into overall_leaderboard
            (user_id, volume, num_sets, reps, num_exercises, num_workouts, duration_mins)
            values
            ($1, $2, $3, $4, $5, $6, $7)
            returning *
            """, user_id, 0.0, 0, 0, 0, 0, 0
        )

    volume = current["volume"] + totals["volume"]
    num_sets = current["num_sets"] + totals["num_sets"]
    reps = current["reps"] + totals["reps"]
    num_exercises = current["num_exercises"] + len(req.exercises)
    num_workouts = current["num_workouts"] + 1
    duration_mins = current["duration_mins"] + req.duration / 1000 / 60

    await conn.execute(
        """
        update overall_leaderboard
        set
            volume = $volume,
            num_sets = $num_sets,
            reps = $reps,
            num_exercises = $num_exercises,
            num_workouts = $num_workouts,
            duration_mins = $duration_mins
        where user_id = $user_id
        """,
        volume=volume,
        num_sets=num_sets,
        reps=reps,
        num_exercises=num_exercises,
        num_workouts=num_workouts,
        duration_mins=duration_mins,
        user_id=user_id,
    )

    # todo send to redis

    r = await redis_connection()

    await r.zadd("overall_volume", {user_id: volume})
    await r.zadd("overall_sets", {user_id: num_sets})
    await r.zadd("overall_reps", {user_id: reps})
    await r.zadd("overall_exercises", {user_id: num_exercises})
    await r.zadd("overall_workouts", {user_id: num_workouts})
    await r.zadd("overall_duration", {user_id: duration_mins})

    # todo add to user specific leaderboard catagories (gender, weight, etc)

@router.get("/workout/overview/stats")
async def workout_overview_stats(credentials: dict = Depends(verify_token)):
    workouts = []

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

        for workout_row in workout_rows:
            totals = {
                "volume": 0,
                "num_sets":  0,
                "reps": 0,
            }
            muscles = {}

            total_rows = await conn.fetch(
                """
                select wsd.reps, wsd.weight, wsd.num_sets
                from workout_set_data wsd
                inner join workout_exercises we
                on wsd.workout_exercise_id = we.id
                where we.workout_id = $1
                """, workout_row["id"]
            )

            for total_row in total_rows:
                totals["volume"] += total_row["reps"] * total_row["weight"] * total_row["num_sets"]
                totals["num_sets"] += total_row["num_sets"]
                totals["reps"] += total_row["reps"]

            muscle_data_list = await conn.fetch(
                """
                select emt.ratio, mt.name target_name, mg.name group_name, wsd.reps, wsd.weight, wsd.num_sets
                from exercises e
                inner join exercise_muscle_targets emt
                on emt.exercise_id = e.id
                inner join muscle_targets mt
                on emt.muscle_target_id = mt.id
                inner join muscle_groups mg
                on mt.muscle_group_id = mg.id
                inner join workout_exercises we
                on we.exercise_id = e.id
                inner join workout_set_data wsd
                on wsd.workout_exercise_id = we.id
                where we.workout_id = $1
                """, workout_row["id"]
            )

            for muscle_data in muscle_data_list:
                group = muscle_data["group_name"]
                target = muscle_data["target_name"]
                if group not in muscles.keys():
                    muscles[group] = {}
                if target not in muscles[group].keys():
                    muscles[group][target] = {
                        "volume": 0,
                        "num_sets": 0,
                        "reps": 0
                    }
                muscles[group][target]["volume"] += (muscle_data["ratio"] / 10) * muscle_data["reps"] * muscle_data["weight"] * muscle_data["num_sets"]
                muscles[group][target]["num_sets"] += muscle_data["num_sets"]
                muscles[group][target]["reps"] += muscle_data["reps"]

            num_exercises = await conn.fetchval(
                """
                select count(*)
                from workout_exercises we
                where we.workout_id = $1
                """, workout_row["id"]
            )

            workouts.append({
                "started_at": datetime_to_timestamp_ms(workout_row["started_at"]),
                "duration": workout_row["duration_secs"],
                "num_exercises": num_exercises,
                "totals": totals,
                "muscles": muscles
            })

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Uncaught exception")
    finally:
        if conn: await conn.close()

    return {
        "workouts": workouts
    }
