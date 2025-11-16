import pytest
from fastapi.testclient import TestClient
import random
import json
import math

from ..main import app
from ..api.middleware.auth_token import decode_token
from ..api.middleware.database import setup_connection
from ..api.middleware.misc import *
from .test_workout_save import get_num_workouts, build_workouts, save_workouts

client = TestClient(app)

@pytest.mark.asyncio
async def test_workout_overview_stats(delete_users, create_user):
    auth_token = create_user
    decoded_auth_token = decode_token(auth_token)
    user_id = decoded_auth_token["user_id"]

    headers = {
        "Authorization": f"Bearer {auth_token}"
    }
    params = {
    }

    try:
        conn = await setup_connection()

        assert 0 == await get_num_workouts(conn, decoded_auth_token)

        response = client.get("/workout/overview/stats", headers=headers, params=params)
        assert response.status_code == 200

        assert response.json()["workouts"] == []

        workouts = await build_workouts(conn, 50, 100)

        await save_workouts(workouts, headers)

        workout_data = []
        for workout in workouts:
            totals = {
                "volume": 0,
                "num_sets":  0,
                "reps": 0,
            }
            muscles = {}
            for exercise in workout["exercises"]:
                rows = await conn.fetch(
                    """
                    select *
                    from exercise_muscle_data
                    where exercise_id = $1
                    """, exercise["id"]
                )
                for row in rows:
                    group_name = row["group_name"]
                    target_name = row["target_name"]
                    if group_name not in muscles:
                        muscles[group_name] = {}
                    if target_name not in muscles[group_name]:
                        muscles[group_name][target_name] = {
                            "volume": 0,
                            "num_sets": 0,
                            "reps": 0
                        }

                    for set_data in exercise["set_data"]:
                        muscles[group_name][target_name]["volume"] += (row["ratio"] / 10) * set_data["reps"] * set_data["weight"] * set_data["num_sets"]
                        muscles[group_name][target_name]["num_sets"] += set_data["num_sets"]
                        muscles[group_name][target_name]["reps"] += set_data["reps"]


                for set_data in exercise["set_data"]:
                    totals["volume"] += set_data["reps"] * set_data["weight"] * set_data["num_sets"]
                    totals["num_sets"] += set_data["num_sets"]
                    totals["reps"] += set_data["reps"]

            workout_data.append({
                "started_at": workout["start_time"],
                "duration": workout["duration"] / 1000,
                "num_exercises": len(workout["exercises"]),
                "totals": totals,
                "muscles": muscles
            })

        response = client.get("/workout/overview/stats", headers=headers, params=params)
        assert response.status_code == 200

        resp_workouts = response.json()["workouts"]
        assert len(resp_workouts) == len(workout_data)
        for workout, resp_workout in zip(workout_data, resp_workouts):
            for key in ["started_at", "duration", "num_exercises"]:
                assert workout[key] == resp_workout[key]
            
            assert workout["totals"] != {}
            for key in workout["totals"]:
                assert workout["totals"][key] == resp_workout["totals"][key]
            
            assert workout["muscles"] != {}
            for group_name, group_data in workout["muscles"].items():
                assert group_data != {}
                for target_name, target_data in group_data.items():
                    assert target_data != {}
                    for key in target_data:
                        assert math.isclose(target_data[key], resp_workout["muscles"][group_name][target_name][key], abs_tol=0.5)

    except Exception as e:
        print(str(e))
        raise e
    finally:
        if conn: await conn.close()