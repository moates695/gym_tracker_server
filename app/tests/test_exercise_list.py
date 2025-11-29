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
from ..api.routes.exercises.history import timespan_to_ms
from ..api.routes.exercises.list_all import get_days_past

client = TestClient(app)

@pytest.mark.asyncio
async def test_exercise_list(delete_users, create_user):
    auth_token = create_user

    headers = {
        "Authorization": f"Bearer {auth_token}"
    }
    params = {
    }

    try:
        conn = await setup_connection()

        workouts = await build_workouts(conn, 20, 40)
        await save_workouts(workouts, headers)

        response = client.get("exercises/list/all", headers=headers, params=params)
        assert response.status_code == 200

        exercises = response.json()["exercises"]
        assert len(exercises) == await conn.fetchval(
            """
            select count(*)
            from exercises
            where parent_id is null
            """
        )

        frequency = {}
        for workout in workouts:
            day_past = get_days_past(datetime.fromtimestamp(workout["start_time"] / 1000))
            if day_past <= 0 or day_past > 28: continue
            day_past = str(day_past)
            for exercise in workout["exercises"]:
                if exercise["id"] not in frequency:
                    frequency[exercise["id"]] = {}
                if day_past not in frequency[exercise["id"]]:
                    frequency[exercise["id"]][day_past] = 0
                volume = 0
                for set_data in exercise["set_data"]:
                    volume += set_data["reps"] * set_data["weight"] * set_data["num_sets"]
                frequency[exercise["id"]][day_past] += volume

        for exercise in response.json()["exercises"]:
            if exercise["id"] not in frequency:
                assert exercise["frequency"] == {}
            else:
                assert len(exercise["frequency"].keys()) == len(frequency[exercise["id"]].keys())
                for key in exercise["frequency"]:
                    assert math.isclose(exercise["frequency"][key], frequency[exercise["id"]][key], abs_tol=0.5)

            assert len(exercise["variations"]) == await conn.fetchval(
                """
                select count(*)
                from exercises
                where parent_id = $1
                """, exercise["id"]
            )
            for variation in exercise["variations"]:
                if variation["id"] not in frequency:
                    assert variation["frequency"] == {}
                else:
                    assert len(variation["frequency"].keys()) == len(frequency[variation["id"]].keys())
                    for key in variation["frequency"]:
                        assert math.isclose(variation["frequency"][key], frequency[variation["id"]][key], abs_tol=0.5)
                
            if exercise["is_body_weight"]:
                for gender in ["male","female"]:
                    assert isinstance(exercise["ratios"][gender], (int, float))
                    assert 0 < exercise["ratios"][gender] <= 1

    except Exception as e:
        print(str(e))
        raise e
    finally:
        if conn: await conn.close()

def test_days_past():
    now_utc = datetime.now(tz=timezone.utc)

    assert get_days_past(now_utc) == 0
    assert get_days_past(now_utc - timedelta(hours=23)) == 0
    assert get_days_past(now_utc - timedelta(hours=24)) == 1
    assert get_days_past(now_utc - timedelta(hours=47)) == 1
    assert get_days_past(now_utc - timedelta(hours=48)) == 2
    assert get_days_past(now_utc - timedelta(days=5)) == 5
    assert get_days_past(now_utc - timedelta(days=30)) == 30

