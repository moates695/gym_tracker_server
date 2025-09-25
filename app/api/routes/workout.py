from fastapi import APIRouter, HTTPException, Security, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import List, Literal
from api.middleware.database import setup_connection
import jwt
import os
from datetime import datetime, timedelta, timezone
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import random
import json
from copy import deepcopy

from api.middleware.auth_token import *
from api.routes.auth import verify_token
from api.middleware.misc import *

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

#? ratio is applied to volume on the client
#? bodyweight determined on the client
@router.post("/workout/save") 
async def workout_save(req: WorkoutSave, credentials: dict = Depends(verify_token)):
    try:
        conn = None
        if len(req.exercises) == 0: return

        conn = await setup_connection()

        start_time = datetime.fromtimestamp(req.start_time / 1000, tz=timezone.utc)
        workout_id = await conn.fetchval(
            """
            insert into workouts
            (user_id, started_at, duration_secs)
            values
            ($1, $2, $3)
            returning id;
            """, credentials["user_id"], start_time, req.duration / 1000
        )

        totals = {
            "volume": 0,
            "num_sets": 0,
            "reps": 0,
        }
        empty_totals = {
            "volume": 0,
            "num_sets": 0,
            "reps": 0,
            "counter": 0
        }
        group_totals = {}
        target_totals = {}

        for i, exercise in enumerate(req.exercises):
            await save_exercise(conn, workout_id, exercise, i)

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

            for set_data in exercise.set_data:
                volume = set_data.reps * set_data.weight * set_data.num_sets

                totals["volume"] += volume
                totals["num_sets"] += set_data.num_sets
                totals["reps"] += set_data.reps

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

            for group_row in group_rows:
                group_totals[group_row["group_id"]]["counter"] += 1

            for target_row in target_rows:
                target_totals[target_row["target_id"]]["counter"] += 1

        current_totals = await conn.fetchrow(
            """
            select *
            from workout_totals
            where user_id = $1
            """, credentials["user_id"]
        )

        if current_totals == None:
            current_totals = await conn.fetch(
                """
                insert into workout_totals
                values
                ($1, 0.0, 0, 0, 0.0, 0, 0)
                returning *
                """, credentials["user_id"]
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
            credentials["user_id"]
        )

        for group_id, group_total in group_totals.items():
            current_group_totals = await conn.fetchrow(
                """
                select *
                from workout_muscle_group_totals
                where user_id = $1
                and muscle_group_id = $2
                """, credentials["user_id"], group_id
            )

            if current_group_totals == None:
                current_group_totals = await conn.fetch(
                    """
                    insert into workout_muscle_group_totals
                    values
                    ($1, $2, 0.0, 0, 0, 0)
                    returning *
                    """, credentials["user_id"], group_id
                )

            await conn.execute(
                """
                update workout_muscle_group_totals
                set
                    volume = $1,
                    num_sets = $2,
                    reps = $3,
                    counter = $4
                where user_id = $5
                and muscle_group_id = $6
                """,
                current_group_totals["volume"] + group_total["volume"],
                current_group_totals["num_sets"] + group_total["num_sets"],
                current_group_totals["reps"] + group_total["reps"],
                current_group_totals["counter"] + group_total["counter"],
                credentials["user_id"],
                group_id
            )

        for target_id, target_total in target_totals.items():
            current_target_totals = await conn.fetchrow(
                """
                select *
                from workout_muscle_target_totals
                where user_id = $1
                and muscle_target_id = $2
                """, credentials["user_id"], target_id
            )

            if current_target_totals == None:
                current_target_totals = await conn.fetch(
                    """
                    insert into workout_muscle_target_totals
                    values
                    ($1, $2, 0.0, 0, 0, 0)
                    returning *
                    """, credentials["user_id"], target_id
                )

            await conn.execute(
                """
                update workout_muscle_target_totals
                set
                    volume = $1,
                    num_sets = $2,
                    reps = $3,
                    counter = $4
                where user_id = $5
                and muscle_target_id = $6
                """,
                current_target_totals["volume"] + target_total["volume"],
                current_target_totals["num_sets"] + target_total["num_sets"],
                current_target_totals["reps"] + target_total["reps"],
                current_target_totals["counter"] + target_total["counter"],
                credentials["user_id"],
                group_id
            )

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
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

@router.get("/workout/overview/stats")
async def workout_overview_stats(use_real: bool, credentials: dict = Depends(verify_token)):
    if use_real:
        return await workout_overview_stats_real(credentials)
    return await workout_overview_stats_rand()

async def workout_overview_stats_real(credentials: dict):
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

async def workout_overview_stats_rand():
    workouts = []
    for _ in range(random.randint(20, 50)):
        muscles = {}
        with open("app/local/muscles.json", "r") as f:
            muscles_json = json.load(f)

        for group, targets in muscles_json.items():
            if random.random() > 0.6: continue
            muscles[group] = {}
            for target in targets:
                if random.random() > 0.9: continue
                muscles[group][target] = {
                    "volume": random.randint(100,900) + random.random(),
                    "num_sets": random.randint(2,6),
                    "reps": random.randint(15,45)
                }

        workouts.append({
            "started_at": random_timestamp_ms(),
            "duration": random.randint(20, 120) * 60 + random.random(),
            "num_exercises": random.randint(3,10),
            "totals": {
                "volume": random_weight() * random.randint(100, 400),
                "num_sets":  random.randint(3, 20),
                "reps": random.randint(30, 250),
            },
            "muscles": muscles
        })

    workouts = sorted(workouts, key=lambda x: x["started_at"], reverse=True)
    
    return {
        "workouts": workouts
    }

# @router.post("/workout/overview/history")
# async def workout_overview_stats(credentials: dict = Depends(verify_token)):
#     return {}