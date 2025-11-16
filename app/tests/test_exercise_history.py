import pytest
from fastapi.testclient import TestClient
from copy import deepcopy
import json
from datetime import datetime, timezone, timedelta
import math

from ..main import app
from ..api.middleware.auth_token import decode_token
from ..tests.test_workout_save import build_workouts, save_workouts
from ..api.middleware.database import setup_connection
from ..api.middleware.misc import datetime_to_timestamp_ms
from ..api.routes.exercises import timespan_to_ms

client = TestClient(app)

# todo: test data returned in correct order (reps ascending, time desending if applicable)
# todo: check returned types are correct (datetime vs timestamp)
@pytest.mark.asyncio
async def test_exercise_history_match(delete_users, create_user):
    auth_token = create_user

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
                "exercise_id": exercise_id
            })
            resp_json = response.json()

            check_n_rep_max_all_time_match(resp_json["n_rep_max"]["all_time"])
            check_n_rep_max_history_match(resp_json["n_rep_max"]["history"])
            check_volume_workout_match(resp_json["volume"]["workout"])
            check_volume_timespan_match(resp_json["volume"]["timespan"])
            check_history_match(resp_json["history"])
            check_points_match(resp_json["reps_sets_weight"])

    except Exception as e:
        print(str(e))
        raise e
    finally:
        if conn: await conn.close()

def check_n_rep_max_all_time_match(n_rep_max_all_time):
    prelim_shape_check(n_rep_max_all_time, ["rep", "weight", "date"])
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

def check_n_rep_max_history_match(n_rep_max_history):
    assert n_rep_max_history != {}
    last_rep = -1
    for rep, history in n_rep_max_history.items():
        prelim_shape_check(history, ["weight", "date"])

        used_timestamps = []
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

            assert graph["x"] not in used_timestamps
            used_timestamps.append(graph["x"])

        assert last_rep < int(rep)
        last_rep = int(rep)

def check_volume_workout_match(volume_workout):
    prelim_shape_check(volume_workout, ["volume", "date"])
    last_timestamp = int(datetime.now(tz=timezone.utc).timestamp())
    for i in range(len(volume_workout["graph"])):
        graph = volume_workout["graph"][i]
        table = volume_workout["table"]["rows"][i]

        graph_date = datetime.fromtimestamp(graph["x"] / 1000).strftime("%d/%m/%Y")
        assert graph_date == table["date"]
        assert graph["y"] == table["volume"]

        assert isinstance(graph["x"], (int, float))
        assert isinstance(graph["y"], (int, float))

        assert isinstance(table["volume"], (int, float))
        assert isinstance(table["date"], str)

        assert last_timestamp >= graph["x"] / 1000
        last_timestamp = graph["x"] / 1000

def check_volume_timespan_match(volume_timespan):
    for timespan in ["week","month","3_months","6_months","year"]:
        data = volume_timespan[timespan]
        prelim_shape_check(data, ["volume", "dates"])

        last_timestamp = int(datetime.now(tz=timezone.utc).timestamp())
        for i in range(len(data["graph"])):
            graph = data["graph"][i]
            table = data["table"]["rows"][i]

            graph_date = datetime.fromtimestamp(graph["x"] / 1000).strftime("%d/%m/%Y")
            assert graph_date == table["dates"].split("-")[1]
            assert graph["y"] == table["volume"]

            assert isinstance(graph["x"], (int, float))
            assert isinstance(graph["y"], (int, float))

            assert isinstance(table["volume"], (int, float))
            assert isinstance(table["dates"], str)

            assert last_timestamp >= int(graph["x"] / 1000)
            last_timestamp = int(graph["x"] / 1000)

            lower_dt = datetime.strptime(table["dates"].split("-")[0], "%d/%m/%Y")
            upper_dt = datetime.strptime(table["dates"].split("-")[1], "%d/%m/%Y")
            assert lower_dt < upper_dt
            
            delta = upper_dt - lower_dt
            match timespan:
                case 'week':
                    assert delta.days == 7
                case 'month':
                    assert 28 <= delta.days <= 31
                case '3_months':
                    assert 88 <= delta.days <= 93
                case '6_months':
                    assert 178 <= delta.days <= 186
                case 'year':
                    assert 365 <= delta.days <= 366

def check_history_match(history):
    assert len(history) > 0
    last_timestamp_ms = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
    for workout in history:
        assert workout["table"]["headers"] == ["reps", "weight", "sets"]
        set_idx = 0
        rep_idx = 0
        assert len(workout["table"]["rows"]) > 0
        for table_row in workout["table"]["rows"]:
            for header in workout["table"]["headers"]:
                assert header in table_row
        
            for _ in range(table_row["sets"]):
                weight_data = workout["graph"]["weight_per_set"][set_idx]
                assert weight_data["x"] == set_idx + 1
                assert weight_data["y"] == table_row["weight"]

                volume_data = workout["graph"]["volume_per_set"][set_idx]
                assert volume_data["x"] == set_idx + 1
                assert volume_data["y"] == table_row["reps"] * table_row["weight"] * table_row["sets"]

                for _ in range(table_row["reps"]):
                    rep_data = workout["graph"]["weight_per_rep"][rep_idx]
                    assert rep_data["x"] == rep_idx + 1
                    assert rep_data["y"] == table_row["weight"]
                    rep_idx += 1
                
                set_idx += 1
            
        assert set_idx == len(workout["graph"]["weight_per_set"])
        assert set_idx == len(workout["graph"]["volume_per_set"])
        assert rep_idx == len(workout["graph"]["weight_per_rep"])

        assert workout["started_at"] < last_timestamp_ms
        last_timestamp_ms = workout["started_at"]

def check_points_match(points):
    assert len(points) > 0
    for point in points:
        for key in ["x", "y", "z"]:
            assert key in point

def prelim_shape_check(data, table_headers):
    assert len(data["graph"]) > 0
    assert len(data["graph"]) == len(data["table"]["rows"])
    assert data["table"]["headers"] == table_headers
    for table_row in data["table"]["rows"]:
        for header in data["table"]["headers"]:
            assert header in table_row.keys()

@pytest.mark.asyncio
async def test_exercise_history_data(delete_users, create_user):
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
                "exercise_id": exercise_id
            })
            resp_json = response.json()
            
            check_n_rep_max_all_time_data(set_data_list, resp_json["n_rep_max"]["all_time"])
            check_n_rep_max_history_data(set_data_list, resp_json["n_rep_max"]["history"])
            check_volume_workout_data(exercise_id, workouts, resp_json["volume"]["workout"])
            check_volume_timespan_data(exercise_id, workouts, resp_json["volume"]["timespan"])
            check_history_data(exercise_id, workouts, resp_json["history"])
            check_points_data(exercise_id, workouts, resp_json["reps_sets_weight"])

    except Exception as e:
        print(str(e))
        raise e
    finally:
        if conn: await conn.close()

def check_n_rep_max_all_time_data(set_data_list, resp_all_time):
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

def check_n_rep_max_history_data(set_data_list, resp_history):
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

        for i in range(len(data)):
            assert data[i]["weight"] == graph[i]["y"]
            assert data[i]["timestamp"] == graph[i]["x"]
    
def check_volume_workout_data(exercise_id, workouts, resp_workout):
    volume_workout = volume_per_workout(exercise_id, workouts)

    assert len(volume_workout) == len(resp_workout["graph"])
    for i in range(len(volume_workout)):
        assert volume_workout[i]["volume"] == resp_workout["graph"][i]["y"]
        assert volume_workout[i]["timestamp"] == resp_workout["graph"][i]["x"]

def check_volume_timespan_data(exercise_id, workouts, resp_timespan):
    volume_workout = volume_per_workout(exercise_id, workouts)

    now_ms = datetime.now(tz=timezone.utc).timestamp() * 1000
    volume_timespan_data = {}
    for timespan in ["week","month","3_months","6_months","year"]:
        timespan_ms = timespan_to_ms(timespan)
        bucket_data = {}
        for workout in volume_workout:
            bucket = int((now_ms - workout["timestamp"]) / timespan_ms)
            if bucket not in bucket_data:
                bucket_data[bucket] = 0
            bucket_data[bucket] += workout["volume"]
        volume_timespan_data[timespan] = dict(sorted(bucket_data.items()))

    for timespan in volume_timespan_data.keys():
        bucket_data = volume_timespan_data[timespan]
        resp_bucket_data = resp_timespan[timespan]
        timespan_ms = timespan_to_ms(timespan)

        assert len(bucket_data.keys()) > 0
        assert len(bucket_data.keys()) == len(resp_bucket_data["graph"])
        for i, (bucket, volume) in enumerate(bucket_data.items()):
            assert volume == resp_bucket_data["graph"][i]["y"]
            assert math.isclose(now_ms - timespan_ms * bucket, resp_bucket_data["graph"][i]["x"], abs_tol=30000)

def volume_per_workout(exercise_id, workouts) -> list[dict]:
    volume_workout = []
    for workout in workouts:
        workout_volume = 0
        for exercise in workout["exercises"]:
            if exercise["id"] != exercise_id: continue
            for set_data in exercise["set_data"]:
                workout_volume += set_data["reps"] * set_data["weight"] * set_data["num_sets"]
        if workout_volume == 0: continue
        volume_workout.append({
            "volume": workout_volume,
            "timestamp": workout["start_time"]
        })
    assert len(volume_workout) > 0
    return sorted(volume_workout, key=lambda e: e["timestamp"], reverse=True)

def check_history_data(exercise_id, workouts, resp_history):
    history = build_history(exercise_id, workouts)

    assert len(history) == len(resp_history)
    for i in range(len(history)):
        assert len(history[i]) == len(resp_history[i]["table"]["rows"])
        for j in range(len(history[i])):
            for key in history[i][j]:
                assert history[i][j][key] == resp_history[i]["table"]["rows"][j][key]

def check_points_data(exercise_id, workouts, resp_points):
    temp_history = build_history(exercise_id, workouts)
    history = []
    for temp in temp_history:
        history.extend(temp)

    assert len(history) == len(resp_points)
    # for i in range(history):
    for hist, resp in zip(history, resp_points):
        assert hist["reps"] == resp["x"]
        assert hist["weight"] == resp["y"]
        assert hist["sets"] == resp["z"]


def build_history(exercise_id, workouts):
    history = []
    for workout in sorted(workouts, key=lambda e: e["start_time"], reverse=True):
        workout_data = []
        for exercise in workout["exercises"]:
            if exercise["id"] != exercise_id: continue
            for set_data in exercise["set_data"]:
                workout_data.append({
                    "reps": set_data["reps"],
                    "weight": set_data["weight"],
                    "sets": set_data["num_sets"],
                })
        if len(workout_data) == 0: continue
        history.append(workout_data)
    assert len(history) > 0
    return history

