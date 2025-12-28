import pytest
from fastapi.testclient import TestClient
import random
import json
import math
from copy import deepcopy

from ..main import app
from ..api.middleware.auth_token import decode_token
from ..api.middleware.database import setup_connection
from ..api.middleware.misc import *
 
client = TestClient(app)

@pytest.mark.asyncio
async def test_save_workout(delete_users, create_user):
    auth_token = create_user
    decoded_auth_token = decode_token(auth_token)
    user_id = decoded_auth_token["user_id"]

    headers = {
        "Authorization": f"Bearer {auth_token}"
    }

    timestamp_ms = 1743561228000
    duration = 50 * 60 * 1000 # Wed Apr 02 2025
    req_body = {
        "exercises": [],
        "start_time": timestamp_ms,
        "duration": duration
    }

    response = client.post("/workout/save", json=req_body, headers=headers)
    assert response.status_code == 200

    try:
        conn = await setup_connection()

        assert 0 == await get_num_workouts(conn, decoded_auth_token)

        lower_lim = 5
        upper_lim = 10
        workouts = await build_workouts(conn, lower_lim, upper_lim)

        await save_workouts(workouts, headers)

        assert len(workouts) == await get_num_workouts(conn, decoded_auth_token)

        await check_correct_save(conn, user_id, workouts)
        await check_workout_totals(conn, user_id, workouts)
        await check_workout_stats(conn, user_id, workouts)
        await check_workout_muscle_target_stats(conn, user_id, workouts)
        await check_workout_muscle_group_stats(conn, user_id, workouts)

    except Exception as e:
        print(str(e))
        raise e
    finally:
        if conn: await conn.close()

async def check_correct_save(conn, user_id, workouts):
    workout_rows = await conn.fetch(
        """
        select w.id, w.started_at, w.duration_secs
        from workouts w
        where w.user_id = $1
        order by w.started_at desc
        """, user_id
    )

    assert len(workouts) == len(workout_rows)
    for workout, workout_row in zip(workouts, workout_rows):
        assert workout["start_time"] == workout_row["started_at"].timestamp() * 1000
        assert workout["duration"] / 1000 == workout_row["duration_secs"]

        workout_exercises_rows = await conn.fetch(
            """
            select id, exercise_id, order_index
            from workout_exercises 
            where workout_id = $1
            order by order_index
            """, workout_row["id"]
        )

        assert len(workout_exercises_rows) == len(workout["exercises"])

        for i, exercise in enumerate(workout["exercises"]):
            workout_exercises_row = workout_exercises_rows[i]
            assert workout_exercises_row["order_index"] == i
            assert str(workout_exercises_row["exercise_id"]) == exercise["id"]

            workout_set_data_rows = await conn.fetch(
                """
                select reps, weight, num_sets, set_class, order_index
                from workout_set_data
                where workout_exercise_id = $1
                order by order_index
                """, workout_exercises_row["id"]
            )

            assert len(exercise["set_data"]) == len(workout_set_data_rows)

            for j, set_data in enumerate(exercise["set_data"]):
                workout_set_data_row = workout_set_data_rows[j]
                assert workout_set_data_row["order_index"] == j
                for muscle_key in ['reps','weight','num_sets','set_class']:
                    assert set_data[muscle_key] == workout_set_data_row[muscle_key]

async def check_workout_totals(conn, user_id, workouts):
    totals = {
        "volume": 0,
        "num_sets": 0,
        "reps": 0,
        "duration": 0,
        "num_workouts": 0,
        "num_exercises": 0
    }
    for workout in workouts:
        totals["num_workouts"] += 1
        totals["duration"] += workout["duration"] / 1000
        for exercise in workout["exercises"]:
            totals["num_exercises"] += 1
            for set_data in exercise["set_data"]:
                totals["volume"] += set_data["reps"] * set_data["weight"] * set_data["num_sets"]
                totals["num_sets"] += set_data["num_sets"]
                totals["reps"] += set_data["reps"]

    db_totals = await conn.fetchrow(
        """
        select *
        from workout_totals
        where user_id = $1
        """, user_id
    )
    
    int_keys = ["num_sets", "reps", "num_workouts", "num_exercises"]
    for muscle_key in int_keys:
        assert totals[muscle_key] == db_totals[muscle_key]

    float_keys = ["volume", "duration"]
    for muscle_key in float_keys:
        assert math.isclose(totals[muscle_key], db_totals[muscle_key], abs_tol=0.5)

    empty_totals = {
        "volume": 0,
        "num_sets": 0,
        "reps": 0,
        "counter": 0
    }

    for muscle_key in ["group", "target"]:
        muscle_total = {}
        rows = await conn.fetch(
            f"""
            select distinct {muscle_key}_id as id
            from muscle_groups_targets
            """
        )
        for row in rows:
            muscle_total[row["id"]] = deepcopy(empty_totals)

        for workout in workouts:
            for exercise in workout["exercises"]:
                rows = await conn.fetch(
                    f"""
                    select distinct on ({muscle_key}_id) ratio, {muscle_key}_id as id
                    from exercise_muscle_data
                    where exercise_id = $1
                    order by {muscle_key}_id, ratio desc
                    """, exercise["id"]
                )
                
                for set_data in exercise["set_data"]:
                    for row in rows:
                        volume = (row["ratio"] / 10) * set_data["reps"] * set_data["weight"] * set_data["num_sets"]
                        muscle_total[row["id"]]["volume"] += volume
                        muscle_total[row["id"]]["num_sets"] += set_data["num_sets"]
                        muscle_total[row["id"]]["reps"] += set_data["reps"]

                for row in rows:
                    muscle_total[row["id"]]["counter"] += 1

        for muscle_id, total in muscle_total.items():
            db_totals = await conn.fetchrow(
                f"""
                select *
                from workout_muscle_{muscle_key}_totals
                where user_id = $1
                and muscle_{muscle_key}_id = $2
                """, user_id, muscle_id
            )

            int_keys = ["num_sets", "reps", "counter"]
            for key in int_keys:
                assert total[key] == db_totals[key]
            assert math.isclose(total["volume"], db_totals["volume"], abs_tol=0.5)

async def check_workout_stats(conn, user_id, workouts):
    workout_stats = await conn.fetch(
        """
        select *
        from previous_workout_stats pws
        inner join workouts w
        on pws.workout_id = w.id
        where w.user_id = $1
        order by w.started_at desc
        """, user_id
    )
    assert len(workouts) == len(workout_stats)
    for workout, workout_stat in zip(workouts, workout_stats):
        totals = {
            "volume": 0,
            "num_sets": 0,
            "reps": 0,
        }
        for exercise in workout["exercises"]:
            for set_data in exercise["set_data"]:
                totals["volume"] += set_data["reps"] * set_data["weight"] * set_data["num_sets"]
                totals["num_sets"] += set_data["num_sets"]
                totals["reps"] += set_data["reps"]

        assert math.isclose(totals["volume"], workout_stat["volume"], abs_tol=0.5)
        assert totals["num_sets"] == workout_stat["num_sets"]
        assert totals["reps"] == workout_stat["reps"]

async def check_workout_muscle_target_stats(conn, user_id, workouts):
    stats_rows = await conn.fetch(
        """
        select *
        from previous_workout_muscle_target_stats p
        inner join workouts w
        on p.workout_id = w.id
        where user_id = $1
        order by w.started_at desc
        """, user_id
    )
    grouped_stats = {}
    for stats_row in stats_rows:
        workout_id = stats_row["workout_id"]
        target_id = stats_row["muscle_target_id"]
        if workout_id not in grouped_stats:
            grouped_stats[workout_id] = {}
        grouped_stats[workout_id][target_id] = {
            "volume": stats_row["volume"],
            "num_sets": stats_row["num_sets"],
            "reps": stats_row["reps"],
        }


    assert len(workouts) == len(grouped_stats.keys())
    for workout, db_stats in zip(workouts, grouped_stats.values()):
        muscle_stats = {}
        for exercise in workout["exercises"]:
            muscle_rows = await conn.fetch(
                """
                select target_id, ratio
                from exercise_muscle_data
                where exercise_id = $1
                """, exercise["id"]
            )
            for muscle_row in muscle_rows:
                for set_data in exercise["set_data"]: 
                    if muscle_row["target_id"] not in muscle_stats:
                        muscle_stats[muscle_row["target_id"]] = {
                            "volume": 0,
                            "num_sets": 0,
                            "reps": 0,
                        }
                    volume = (muscle_row["ratio"] / 10) * set_data["reps"] * set_data["weight"] * set_data["num_sets"]
                    muscle_stats[muscle_row["target_id"]]["volume"] += volume
                    muscle_stats[muscle_row["target_id"]]["num_sets"] += set_data["num_sets"]
                    muscle_stats[muscle_row["target_id"]]["reps"] += set_data["reps"]

        assert len(muscle_stats.keys()) == len(db_stats.keys())             
        for key in muscle_stats:
            assert math.isclose(muscle_stats[key]["volume"], db_stats[key]["volume"], abs_tol=0.5)
            for int_key in ["num_sets", "reps"]:
                assert muscle_stats[key][int_key] == db_stats[key][int_key]

async def check_workout_muscle_group_stats(conn, user_id, workouts):
    stats_rows = await conn.fetch(
        """
        select *
        from previous_workout_muscle_group_stats p
        inner join workouts w
        on p.workout_id = w.id
        where user_id = $1
        order by w.started_at desc
        """, user_id
    )
    grouped_stats = {}
    for stats_row in stats_rows:
        workout_id = stats_row["workout_id"]
        group_id = stats_row["muscle_group_id"]
        if workout_id not in grouped_stats:
            grouped_stats[workout_id] = {}
        grouped_stats[workout_id][group_id] = {
            "volume": stats_row["volume"],
            "num_sets": stats_row["num_sets"],
            "reps": stats_row["reps"],
        }


    assert len(workouts) == len(grouped_stats.keys())
    for workout, db_stats in zip(workouts, grouped_stats.values()):
        muscle_stats = {}
        for exercise in workout["exercises"]:
            muscle_rows = await conn.fetch(
                """
                select distinct on (group_id) ratio, group_id
                from exercise_muscle_data
                where exercise_id = $1
                order by group_id, ratio desc
                """, exercise["id"]
            )
            for muscle_row in muscle_rows:
                for set_data in exercise["set_data"]: 
                    if muscle_row["group_id"] not in muscle_stats:
                        muscle_stats[muscle_row["group_id"]] = {
                            "volume": 0,
                            "num_sets": 0,
                            "reps": 0,
                        }
                    volume = (muscle_row["ratio"] / 10) * set_data["reps"] * set_data["weight"] * set_data["num_sets"]
                    muscle_stats[muscle_row["group_id"]]["volume"] += volume
                    muscle_stats[muscle_row["group_id"]]["num_sets"] += set_data["num_sets"]
                    muscle_stats[muscle_row["group_id"]]["reps"] += set_data["reps"]

        assert len(muscle_stats.keys()) == len(db_stats.keys())             
        for key in muscle_stats:
            assert math.isclose(muscle_stats[key]["volume"], db_stats[key]["volume"], abs_tol=0.5)
            for int_key in ["num_sets", "reps"]:
                assert muscle_stats[key][int_key] == db_stats[key][int_key]

async def save_workouts(workouts, headers, skip_fail=False):
    for workout in workouts:
        try:
            response = client.post("/workout/save", json=workout, headers=headers)
            assert response.status_code == 200
        except Exception as e:
            if skip_fail: continue
            raise e

# todo: test empty save
# todo: test invalid saves

# todo: check that if register misses workout_totals (+ others) that the workout save func inserts baseline

async def build_workouts(conn, lower_lim=5, upper_lim=10, recent=False):
    workouts = []
    start_timestamps = []
    for _ in range(random.randint(lower_lim, upper_lim)):
        if recent:
            while 1:
                start_time = now_timestamp_ms() - random.randint(0, 30*24*60*60*1000)
                if start_time in start_timestamps: continue
                start_timestamps.append(start_time)
                break
        else:
            while 1:
                start_time = int(random_timestamp_ms())
                if start_time in start_timestamps: continue
                start_timestamps.append(start_time)
                break

        duration = random.randint(5*60, 120*60) * 1000
        rows = await conn.fetch(
            """
            select id
            from exercises
            """
        )
        all_exercise_ids = [str(row["id"]) for row in rows]
        exercise_ids = random.sample(all_exercise_ids, random.randint(2,8))

        exercises = []
        for exercise_id in exercise_ids:
            set_data = []
            for _ in range(random.randint(1,5)):
                set_data.append({
                    "reps": random.randint(3,15),
                    "weight": random_weight(),
                    "num_sets": random.randint(1,5),
                    "set_class": random.sample(set_classes, 1)[0]
                })
            
            exercises.append({
                "id": exercise_id,
                "set_data": set_data
            })

        workouts.append({
            "exercises": exercises,
            "start_time": start_time,
            "duration": duration
        })

    return sorted(workouts, key=lambda e: e["start_time"], reverse=True)

@pytest.mark.asyncio
async def test_build_workouts(delete_users, create_user):
    try:
        conn = await setup_connection()
        
        lower_lim = 6
        upper_lim = 12
        for _ in range(10):
            workouts = await build_workouts(conn, lower_lim, upper_lim)
            assert len(workouts) >= lower_lim
            assert len(workouts) <= upper_lim

            last_timestamp_ms = now_timestamp_ms()
            for workout in workouts:
                for exercise in workout["exercises"]:
                    assert len(exercise["set_data"]) > 0
                    for data in exercise["set_data"]:
                        for key, value in data.items():
                            if key == 'set_class':
                                assert value in set_classes
                                continue
                            assert value > 0
            
                assert last_timestamp_ms >= workout["start_time"]
                last_timestamp_ms = workout["start_time"]

    except Exception as e:
        print(str(e))
        raise e
    finally:
        if conn: await conn.close()

async def get_num_workouts(conn, decoded):
    return await conn.fetchval(
        """
        select count(*)
        from workouts w
        where user_id = $1
        """, decoded["user_id"]
    )

set_classes = ['working', 'dropset', 'warmup', 'cooldown']


