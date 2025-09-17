import pytest
from fastapi.testclient import TestClient
from copy import deepcopy
import json
from datetime import datetime, timezone

from ..main import app
from ..api.middleware.auth_token import decode_token
from ..tests.test_workout_save import build_workouts, save_workouts
from ..api.middleware.database import setup_connection

client = TestClient(app)

# todo: test data returned in correct order (reps ascending, time desending if applicable)
@pytest.mark.asyncio
async def test_exercise_history_match(delete_test_users, create_user):
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

        exercise_ids = set()
        for workout in workouts:
            for exercise in workout["exercises"]:
                exercise_ids.add(exercise["id"])
        exercise_ids = list(exercise_ids)

        assert len(exercise_ids) > 0
        for exercise_id in exercise_ids:
            response = client.get('/exercise/history', headers=headers, params={
                'use_real': True,
                "exercise_id": exercise_id
            })
            resp_json = response.json()

            n_rep_max_all_time = resp_json["n_rep_max"]["all_time"]
            assert len(n_rep_max_all_time["graph"]) > 0
            assert len(n_rep_max_all_time["graph"]) == len(n_rep_max_all_time["table"]["rows"])
            assert n_rep_max_all_time["table"]["headers"] == ["rep", "weight", "date"]
            for table_row in n_rep_max_all_time["table"]["rows"]:
                for header in n_rep_max_all_time["table"]["headers"]:
                    assert header in table_row.keys()

            last_rep = -1
            # last_timestamp = int(datetime.now(tz=timezone.utc).timestamp())
            for i in range(len(n_rep_max_all_time["graph"])):
                graph = n_rep_max_all_time["graph"][i]
                table = n_rep_max_all_time["table"]["rows"][i]
                assert graph["x"] == table["rep"]
                assert graph["y"] == table["weight"]

                assert last_rep < graph['x']
                last_rep = graph['x']

    except Exception as e:
        print(str(e))
        assert False
    finally:
        if conn: await conn.close()

@pytest.mark.asyncio
async def test_exercise_history_data(delete_test_users, create_user):
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

        exercises = {}
        for workout in workouts:
            for exercise in workout["exercises"]:
                if exercise["id"] not in exercises:
                    exercises[exercise["id"]] = []
                set_data = deepcopy(exercise["set_data"])
                for temp in set_data:
                    temp["timestamp"] = workout["start_time"]
                exercises[exercise["id"]].extend(set_data)

        for exercise_id, set_data_list in exercises.items():
            response = client.get('/exercise/history', headers=headers, params={
                "use_real": True,
                "exercise_id": exercise_id
            })
            resp_json = response.json()
            
            n_rep_max_all_time = {}
            for set_data in set_data_list:
                curr_max = n_rep_max_all_time.get(set_data["reps"], {'weight': 0})["weight"]
                if set_data["weight"] <= curr_max: continue
                n_rep_max_all_time[set_data["reps"]] = {
                    "weight": set_data["weight"],
                    "timestamp": set_data["timestamp"]
                }
            n_rep_max_all_time = dict(sorted(n_rep_max_all_time.items()))

            assert len(n_rep_max_all_time.keys()) == len(resp_json["n_rep_max"]["all_time"]["graph"])
            for i, (rep, data) in enumerate(n_rep_max_all_time.items()):
                assert resp_json["n_rep_max"]["all_time"]["graph"][i]["x"] == rep
                assert resp_json["n_rep_max"]["all_time"]["graph"][i]["y"] == data["weight"]


    except Exception as e:
        print(str(e))
        assert False
    finally:
        if conn: await conn.close()

    # todo: create workouts and then test the exercise history function
