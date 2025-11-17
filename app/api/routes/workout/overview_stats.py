from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from app.api.middleware.database import setup_connection
from app.api.middleware.auth_token import *
from app.api.routes.auth import verify_token
from app.api.middleware.misc import *

router = APIRouter()

@router.get("/overview/stats")
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