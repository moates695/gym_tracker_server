import pytest
from fastapi.testclient import TestClient
from copy import deepcopy
import json

from ..main import app
from ..api.middleware.auth_token import decode_token
from ..tests.test_workout_save import build_workouts, save_workouts
from ..api.middleware.database import setup_connection

client = TestClient(app)

@pytest.mark.asyncio
async def test_exercise_history(delete_test_users, create_user):
    auth_token = create_user
    decoded_auth_token = decode_token(auth_token)
    user_id = decoded_auth_token["user_id"]

    headers = {
        "Authorization": f"Bearer {auth_token}"
    }
    params = {
        "use_real": True
    }

    try:
        conn = await setup_connection()

        lower_lim = 10
        upper_lim = 20
        workouts = await build_workouts(conn, lower_lim, upper_lim)
        await save_workouts(workouts, headers)

        # exercises = {}
        for workout in workouts:
            for exercise in workout["exercises"]:
                # if exercise["id"] not in exercises:
                #     exercises[exercise["id"]] = []
                # set_data = deepcopy(exercise["set_data"])
                # for temp in set_data:
                #     temp["timestamp"] = workout["start_time"]
                # exercises[exercise["id"]].append(set_data)

                n_rep_max_all_time = {}
                for set_data in exercise["set_data"]:
                    curr_max = n_rep_max_all_time.get(set_data["reps"], {"weight": 0})["weight"]
                    if curr_max <= set_data["weight"]: continue
                    n_rep_max_all_time[set_data["reps"]] = {
                        "weight": set_data["weight"],
                        "timestamp": workout["start_time"]
                    }

                response = client.get("/exercise/history", headers=headers, params={
                    "use_real": True,
                    "exercise_id": exercise["id"]
                })

                print(response.status_code)
                print(response.json())
                assert False

        # for temp in exercises.values():
        #     print(json.dumps(temp, indent=2))
        #     assert False      
        # for exercise_id, exercise in exercises.items():
        #     n_rep_max_all_time = {}
        #     for data in set_data:
        #         curr_max = n_rep_max_all_time.get(data["reps"], {"weight": 0})["weight"]
        #         if curr_max <= data["weight"]: continue
        #         n_rep_max_all_time[data["reps"]] = {
        #             "weight": data["weight"]

        #         }

    except Exception as e:
        print(str(e))
        assert False
    finally:
        if conn: await conn.close()

    # todo: create workouts and then test the exercise history function
