import pytest
from fastapi.testclient import TestClient
import random

from ..main import app
from ..api.middleware.auth_token import decode_token
from ..api.middleware.database import setup_connection
 
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

    try:
        conn = await setup_connection()

        assert 0 == await conn.fetchval(
            """
            select count(*)
            from workouts w
            where user_id = $1
            """, decoded_auth_token["user_id"]
        )

        workouts = []
        for _ in range(random.randint(5, 10)):
            base_exercise_ids = await conn.fetch



        # exercises = [
        #     {
        #         'name': 'Bench Press',
        #         'parent_name': None
        #     },
        #     {
        #         'name': 'Push-Up',
        #         'parent_name': None
        #     },
        #     {
        #         'name': 'flat bar, close grip',
        #         'parent_name': 'Cable Tricep Extension'
        #     }
        # ]

        # for exercise_data in exercises:
        #     if exercise_data["parent_name"] is None:
        #         exercise_id = await conn.fetchval(
        #             """
        #             select id
        #             from exercises
        #             where name = $1
        #             """, exercise_data["name"]
        #         )
        #     else:
        #         exercise_id = await conn.fetchval(
        #             """
        #             select e2.id
        #             from exercises e1
        #             left join exercises e2
        #             on e2.parent_id = e1.id
        #             where e1.name = $1
        #             and e2.name = $2
        #             """, exercise_data["parent_name"], exercise_data["name"]
        #         )

        # timestamp_ms = 1743561228000
        # duration = 50 * 60 * 1000
        # # Wed Apr 02 2025
        # req_body = {
        #     "exercises": [],
        #     "start_time": timestamp_ms,
        #     "duration": duration
        # }

        # response = client.post("/workout/save", json=req_body, headers=headers)
        # assert response.status_code == 200

    except Exception as e:
        print(str(e))
        assert False
    finally:
        if conn: await conn.close()
