import pytest
from fastapi.testclient import TestClient
from copy import deepcopy
import json
from datetime import datetime, timezone
import math

from ..main import app
from ..api.middleware.auth_token import decode_token
from ..tests.test_workout_save import build_workouts, save_workouts
from ..api.middleware.database import setup_connection
from..api.middleware.misc import datetime_to_timestamp_ms

client = TestClient(app)

# todo: test data returned in correct order (reps ascending, time desending if applicable)
# todo: check returned types are correct (datetime vs timestamp)
@pytest.mark.asyncio
async def test_exercise_history_match(delete_test_users, create_user):
    auth_token = create_user
    decoded_auth_token = decode_token(auth_token)
    user_id = decoded_auth_token["user_id"]

    headers = {
        "Authorization": f"Bearer {auth_token}"
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
            for i in range(len(n_rep_max_all_time["graph"])):
                graph = n_rep_max_all_time["graph"][i]
                table = n_rep_max_all_time["table"]["rows"][i]
                
                assert graph["x"] == table["rep"]
                assert graph["y"] == table["weight"]

                assert isinstance(graph["x"], (int, float))
                assert isinstance(graph["y"], (int, float))

                assert isinstance(table["rep"], (int, float))
                assert isinstance(table["weight"], (int, float))
                assert isinstance(table["date"], str)

                assert last_rep < graph['x']
                last_rep = graph['x']

            last_rep = -1
            n_rep_max_history = resp_json["n_rep_max"]["history"]
            assert n_rep_max_history != {}
            for rep, history in n_rep_max_history.items():
                assert len(history["graph"]) > 0
                assert len(history["graph"]) == len(history["table"]["rows"]) 
                assert history["table"]["headers"] == ["weight", "date"]
                for table_row in history["table"]["rows"]:
                    for header in history["table"]["headers"]:
                        assert header in table_row.keys()

                last_timestamp = int(datetime.now(tz=timezone.utc).timestamp())
                for i in range(len(history["graph"])):
                    graph = history["graph"][i]
                    table = history["table"]["rows"][i]
                    
                    graph_date = datetime.fromtimestamp(graph["x"] / 1000).strftime("%d/%m/%Y")
                    assert graph_date == table["date"]
                    assert graph["y"] == table["weight"]

                    assert isinstance(graph["x"], (int, float))
                    assert isinstance(graph["y"], (int, float))

                    assert isinstance(table["weight"], (int, float))
                    assert isinstance(table["date"], str)

                    assert last_timestamp >= graph["x"] / 1000
                    last_timestamp = graph["x"] / 1000

                assert last_rep < int(rep)
                last_rep = int(rep)

    except Exception as e:
        print(str(e))
        raise e
    finally:
        if conn: await conn.close()

@pytest.mark.asyncio
async def test_exercise_history_data(delete_test_users, create_user):
    auth_token = create_user
    # decoded_auth_token = decode_token(auth_token)
    # user_id = decoded_auth_token["user_id"]

    headers = {
        "Authorization": f"Bearer {auth_token}"
    }

    try:
        conn = await setup_connection()

        lower_lim = 20
        upper_lim = 30
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
            
            n_rep_max_all_time_func(set_data_list, resp_json["n_rep_max"]["all_time"])
            n_rep_max_history_func(set_data_list, resp_json["n_rep_max"]["history"])
            # volume_workout_func(set_data_list, resp_json["volume"]["workout"])

    except Exception as e:
        print(str(e))
        raise e
    finally:
        if conn: await conn.close()

def n_rep_max_all_time_func(set_data_list, resp_all_time):
    n_rep_max_all_time = {}
    for set_data in set_data_list:
        curr_max = n_rep_max_all_time.get(set_data["reps"], {'weight': -math.inf})["weight"]
        if curr_max > set_data["weight"]: continue
        n_rep_max_all_time[set_data["reps"]] = {
            "weight": set_data["weight"],
            "timestamp": set_data["timestamp"]
        }

    n_rep_max_all_time = dict(sorted(n_rep_max_all_time.items()))

    assert len(n_rep_max_all_time.keys()) > 0
    assert len(n_rep_max_all_time.keys()) == len(resp_all_time["graph"])
    for i, (rep, data) in enumerate(n_rep_max_all_time.items()):
        assert resp_all_time["graph"][i]["x"] == rep
        assert resp_all_time["graph"][i]["y"] == data["weight"]

def n_rep_max_history_func(set_data_list, resp_history):
    n_rep_max_history_data = {}
    for set_data in set_data_list:
        if set_data["reps"] not in n_rep_max_history_data.keys():
            n_rep_max_history_data[set_data["reps"]] = {}
        rep_data = n_rep_max_history_data[set_data["reps"]]
        timestamp = set_data["timestamp"]

        curr_max = rep_data.get(timestamp, -math.inf)
        if curr_max > set_data["weight"]: continue
        rep_data[timestamp] = set_data["weight"]

    n_rep_max_history = {}
    for rep, weight_data in n_rep_max_history_data.items():
        if rep not in n_rep_max_history:
            n_rep_max_history[rep] = []
        for timestamp, weight in weight_data.items():
            n_rep_max_history[rep].append({
                "weight": weight,
                "timestamp": timestamp
            })

    for rep, weight_data in n_rep_max_history.items():
        n_rep_max_history[rep] = sorted(weight_data, key=lambda e: e["timestamp"], reverse=True)

    assert len(n_rep_max_history.keys()) > 0
    assert len(n_rep_max_history.keys()) == len(resp_history.keys())
    
    for rep, data in n_rep_max_history.items():
        graph = resp_history[str(rep)]["graph"]
        assert len(data) > 0
        assert len(data) == len(graph)

        used_timestamps = []
        for i in range(len(data)):
            assert data[i]["weight"] == graph[i]["y"]
            assert data[i]["timestamp"] == graph[i]["x"]

            if graph[i]["x"] in used_timestamps: assert False
            used_timestamps.append(graph[i]["x"])
    
def volume_workout_func(set_data_list, resp_workout):
    pass

# todo: create workouts and then test the exercise history function

