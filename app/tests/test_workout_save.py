import pytest
from fastapi.testclient import TestClient
import random
import json

from ..main import app
from ..api.middleware.auth_token import decode_token
from ..api.middleware.database import setup_connection
from ..api.middleware.misc import *
 
client = TestClient(app)

@pytest.mark.asyncio
async def test_workout_save(delete_test_users, create_user):
    auth_token = create_user
    decoded_auth_token = decode_token(auth_token)
    user_id = decoded_auth_token["user_id"]

    headers = {
        "Authorization": f"Bearer {auth_token}"
    }

    timestamp_ms = 1743561228000
    duration = 50 * 60 * 1000
    # Wed Apr 02 2025
    req_body = {
        "exercises": [],
        "start_time": timestamp_ms,
        "duration": duration
    }

    response = client.post("/workout/save", json=req_body, headers=headers)
    assert response.status_code == 200

    set_classes = ['working', 'dropset', 'warmup', 'cooldown']

    try:
        conn = await setup_connection()

        assert 0 == await get_num_workouts(conn, decoded_auth_token)

        workouts = []
        workout_num_lower_lim = 5
        for _ in range(random.randint(workout_num_lower_lim, 10)):
            start_time = int(random_timestamp_ms())
            duration = random.randint(5*60, 120*60)
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

            response = client.post("/workout/save", json=workouts[-1], headers=headers)
            assert response.status_code == 200

        assert len(workouts) >= workout_num_lower_lim
        assert len(workouts) == await get_num_workouts(conn, decoded_auth_token)


    except Exception as e:
        print(str(e))
        assert False
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
