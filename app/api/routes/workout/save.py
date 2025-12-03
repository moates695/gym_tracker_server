from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Literal
from datetime import datetime, timezone
from copy import deepcopy
import traceback

from app.api.middleware.database import setup_connection, redis_connection
from app.api.middleware.auth_token import *
from app.api.routes.auth import verify_token
from app.api.middleware.misc import *

router = APIRouter()

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

# todo update redis with new leaderboard data
#? bodyweight determined on the client
@router.post("/save") 
async def workout_save(req: WorkoutSave, credentials: dict = Depends(verify_token)):
    conn = tx = None
    try:
        user_id = credentials["user_id"]

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
            "workout": {
                "volume": 0,
                "num_sets": 0,
                "reps": 0,
            },
            "group": {},
            "target": {}
        }

        for i, exercise in enumerate(req.exercises):
            await save_exercise(conn, workout_id, exercise, i)
            await process_exercise(conn, user_id, exercise, totals)

        await update_workout_totals(conn, user_id, totals, req)
        await update_muscle_totals(conn, user_id, totals)
        await update_previous_stats(conn, workout_id, totals, req)
        await update_overall_leaderboard(conn, user_id, totals, req)

        await tx.commit()
    
    except SafeError as e:
        if tx: await tx.rollback()
        raise e
    except Exception as e:
        print(str(e))
        if tx: await tx.rollback()
        traceback.print_exc()
        raise Exception('uncaught error')
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

async def process_exercise(conn, user_id, exercise: Exercise, totals):
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
        process_exercise_sets(set_data, totals, exercise_totals, group_rows, target_rows)

    for group_row in group_rows:
        totals["group"][group_row["group_id"]]["counter"] += 1

    for target_row in target_rows:
        totals["target"][target_row["target_id"]]["counter"] += 1

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

    await update_exercise_leaderboards(conn, user_id, exercise, exercise_totals)

def process_exercise_sets(set_data, totals, exercise_totals, group_rows, target_rows):
    empty_totals = {
        "volume": 0,
        "num_sets": 0,
        "reps": 0,
        "counter": 0
    }

    volume = set_data.reps * set_data.weight * set_data.num_sets

    totals["workout"]["volume"] += volume
    totals["workout"]["num_sets"] += set_data.num_sets
    totals["workout"]["reps"] += set_data.reps

    exercise_totals["volume"] += volume
    exercise_totals["num_sets"] += set_data.num_sets
    exercise_totals["reps"] += set_data.reps

    for group_row in group_rows:
        if group_row["group_id"] not in totals["group"]:
            totals["group"][group_row["group_id"]] = deepcopy(empty_totals)
        totals["group"][group_row["group_id"]]["volume"] += (group_row["ratio"] / 10) * volume
        totals["group"][group_row["group_id"]]["num_sets"] += set_data.num_sets
        totals["group"][group_row["group_id"]]["reps"] += set_data.reps

    for target_row in target_rows:
        if target_row["target_id"] not in totals["target"]:
            totals["target"][target_row["target_id"]] = deepcopy(empty_totals)
        totals["target"][target_row["target_id"]]["volume"] += (target_row["ratio"] / 10) * volume
        totals["target"][target_row["target_id"]]["num_sets"] += set_data.num_sets
        totals["target"][target_row["target_id"]]["reps"] += set_data.reps

async def update_workout_totals(conn, user_id, totals, req):
    current_totals = await conn.fetchrow(
        """
        select *
        from workout_totals
        where user_id = $1
        """, user_id
    )

    if current_totals == None:
        current_totals = await conn.fetchrow(
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
        current_totals["volume"] + totals["workout"]["volume"],
        current_totals["num_sets"] + totals["workout"]["num_sets"],
        current_totals["reps"] + totals["workout"]["reps"],
        current_totals["duration"] + req.duration / 1000,
        current_totals["num_workouts"] + 1,
        current_totals["num_exercises"] + len(req.exercises),
        user_id
    )

async def update_muscle_totals(conn, user_id, totals):
    for key in ["group", "target"]:
        muscle_totals = totals["group"] if key == "group" else totals["target"]
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
                current_muscle_totals = await conn.fetchrow(
                    f"""
                    insert into workout_muscle_{key}_totals
                    (user_id, muscle_{key}_id, volume, num_sets, reps, counter)
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

async def update_previous_stats(conn, workout_id, totals, req: WorkoutSave):
    await conn.execute(
        """
        insert into previous_workout_stats
        (workout_id, volume, num_sets, reps, num_exercises)
        values
        ($1, $2, $3, $4, $5)
        """, workout_id, totals["workout"]["volume"], totals["workout"]["num_sets"], totals["workout"]["reps"], len(req.exercises)
    )

    for group_id, group_total in totals["group"].items():
        await conn.execute(
            """
            insert into previous_workout_muscle_group_stats
            (workout_id, muscle_group_id, volume, num_sets, reps)
            values
            ($1, $2, $3, $4, $5)
            """, workout_id, group_id, group_total["volume"], group_total["num_sets"], group_total["reps"]
        )

    for target_id, target_total in totals["target"].items():
        await conn.execute(
            """
            insert into previous_workout_muscle_target_stats
            (workout_id, muscle_target_id, volume, num_sets, reps)
            values
            ($1, $2, $3, $4, $5)
            """, workout_id, target_id, target_total["volume"], target_total["num_sets"], target_total["reps"]
        )

async def update_overall_leaderboard(conn, user_id, totals, req: WorkoutSave):
    current = await conn.fetchrow(
        """
        select *
        from overall_leaderboard
        where user_id = $1
        """, user_id
    )

    if current is None:
        current = await conn.fetchrow(
            """
            insert into overall_leaderboard
            (user_id, volume, num_sets, reps, num_exercises, num_workouts, duration_mins)
            values
            ($1, $2, $3, $4, $5, $6, $7)
            returning *
            """, user_id, 0.0, 0, 0, 0, 0, 0
        )

    volume = current["volume"] + totals["workout"]["volume"]
    num_sets = current["num_sets"] + totals["workout"]["num_sets"]
    reps = current["reps"] + totals["workout"]["reps"]
    num_exercises = current["num_exercises"] + len(req.exercises)
    num_workouts = current["num_workouts"] + 1
    duration_mins = current["duration_mins"] + req.duration / 1000 / 60

    await conn.execute(
        """
        update overall_leaderboard
        set
            volume = $1,
            num_sets = $2,
            reps = $3,
            num_exercises = $4,
            num_workouts = $5,
            duration_mins = $6,
            last_updated = now() at time zone 'utc'
        where user_id = $7
        """,
        volume,
        num_sets,
        reps,
        num_exercises,
        num_workouts,
        duration_mins,
        user_id,
    )

    r = await redis_connection()

    data_map = {
        "overall:volume:leaderboard": volume,
        "overall:sets:leaderboard": num_sets,
        "overall:reps:leaderboard": reps,
        "overall:exercises:leaderboard": num_exercises,
        "overall:workouts:leaderboard": num_workouts,
        "overall:duration:leaderboard": duration_mins,
    }
    for key, value in data_map.items():
        await r.zadd(key, {
            user_id: value
        })

    # todo add to user specific leaderboard catagories (gender, weight, etc)

async def update_exercise_leaderboards(conn, user_id, exercise: Exercise, exercise_totals):
    current = await conn.fetchrow(
        """
        select *
        from exercises_leaderboard
        where user_id = $1
        and exercise_id = $2
        """, user_id, exercise.id
    )

    if current is None:
        current = await conn.fetchrow(
            """
            insert into exercises_leaderboard
            (user_id, exercise_id, volume, num_sets, reps, num_workouts)
            values
            ($1, $2, $3, $4, $5, $6)
            returning *
            """, user_id, exercise.id, 0.0, 0, 0, 0
        )

    volume = current["volume"] + exercise_totals["volume"]
    num_sets = current["num_sets"] + exercise_totals["num_sets"]
    reps = current["reps"] + exercise_totals["reps"]
    num_workouts = current["num_workouts"] + 1

    await conn.execute(
        """
        update exercises_leaderboard
        set
            volume = $1,
            num_sets = $2,
            reps = $3,
            num_workouts = $4,
            last_updated = now() at time zone 'utc'
        where user_id = $5
        """,
        volume,
        num_sets,
        reps,
        num_workouts,
        user_id,
    )

    r = await redis_connection()

    metrics = {
        "volume": volume, 
        "sets": num_sets, 
        "reps": reps, 
        "workouts": num_workouts
    }
    for metric, value in metrics.items():
        leaderboard = exercise_zset_name(
            exercise_id=exercise.id, 
            metric=metric
        )
        await r.zadd(leaderboard, {
            user_id: value
        })