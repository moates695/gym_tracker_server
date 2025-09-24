import pytest
from fastapi.testclient import TestClient
import random
import json

from ..main import app
from ..api.middleware.auth_token import decode_token
from ..api.middleware.database import setup_connection
from ..api.middleware.misc import *
from .test_workout_save import get_num_workouts, build_workouts, save_workouts

client = TestClient(app)

@pytest.mark.asyncio
async def test_workout_overview_stats(delete_test_users, create_user):
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

        assert 0 == await get_num_workouts(conn, decoded_auth_token)

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
                for set_data in exercise["set_data"]:
                    totals["volume"] += set_data["reps"] * set_data["weight"] * set_data["num_sets"]
                    totals["num_sets"] += set_data["num_sets"]
                    totals["reps"] += set_data["reps"]

            workout_data.append({
                "started_at": workout["start_time"],
                "duration": workout["duration"],
                "num_exercises": len(workout["exercises"]),
                "totals": totals,
                "muscles": muscles
            })

        response = client.get("/workout/overview/stats", headers=headers, params=params)
        assert response.status_code == 200

        assert len(response.json()["workouts"]) == len(workout_data)

    except Exception as e:
        print(str(e))
        raise e
    finally:
        if conn: await conn.close()