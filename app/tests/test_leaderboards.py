import pytest
from fastapi.testclient import TestClient
from copy import deepcopy
import json
from datetime import datetime, timezone, timedelta
import math
from uuid import uuid4
import os

from ..main import app
from ..api.middleware.auth_token import decode_token, generate_token
from ..tests.test_workout_save import build_workouts, save_workouts
from ..api.middleware.database import setup_connection
from ..api.middleware.misc import datetime_to_timestamp_ms
from ..api.routes.exercises import timespan_to_ms
from ..tests.test_register import valid_user

client = TestClient(app)

@pytest.mark.asyncio
async def test_overall_volume(delete_users, create_user):
    pass

@pytest.mark.asyncio
async def test_overall_volume(delete_users):
    top_num = 10
    side_num = 20
    params = {
        "top_num": top_num,
        "side_num": side_num
    }
    expected_len = top_num + 2 * side_num + 1
    num_users = 3 * expected_len

    try:
        conn = await setup_connection()

        user_data = []
        for i in range(num_users):
            email = str(uuid4())
            username = str(uuid4())
            user_id = await conn.fetchval(
                """
                insert into users
                (email, password, username, first_name, last_name, gender)
                values
                ($1, $2, $3, $4, $5, $6)
                returning id
                """, email, str(uuid4()), username, str(uuid4()), str(uuid4()), 'male'
            )
            user_data.append({
                "user_id": user_id,
                "email": email,
                "token": generate_token(email, user_id, minutes=5),
                "username": username
            })

            await conn.execute(
                """
                insert into volume_leaderboard
                (user_id, volume, last_updated)
                values
                ($1, $2, $3)
                """, user_id, i, datetime.now(tz=timezone.utc).replace(tzinfo=None)
            )
        user_data.reverse()

        # ranked first
        response = client.get(
            "/stats/leaderboards/overall/volume", 
            headers=getHeaders(user_data[0]["token"]),
            params=params,
        )
        assert response.status_code == 200
        resp_json = response.json()
        assert resp_json["fracture"] is None
        assert len(resp_json["leaderboard"]) == expected_len
        for i in range(expected_len):
            assert resp_json["leaderboard"][i]["rank"] == i + 1
            assert resp_json["leaderboard"][i]["username"] == user_data[i]["username"]

        # ranked just inside of fracture limit
        user_idx = top_num + side_num
        response = client.get(
            "/stats/leaderboards/overall/volume", 
            headers=getHeaders(user_data[user_idx]["token"]),
            params=params,
        )
        assert response.status_code == 200
        resp_json = response.json()
        assert resp_json["fracture"] is None
        assert len(resp_json["leaderboard"]) == expected_len
        for i in range(expected_len):
            assert resp_json["leaderboard"][i]["rank"] == i + 1
            assert resp_json["leaderboard"][i]["username"] == user_data[i]["username"]

        # ranked just outside of fracture limit
        user_idx = top_num + side_num + 1
        response = client.get(
            "/stats/leaderboards/overall/volume", 
            headers=getHeaders(user_data[user_idx]["token"]),
            params=params,
        )
        assert response.status_code == 200
        resp_json = response.json()
        assert resp_json["fracture"] == top_num
        assert len(resp_json["leaderboard"]) == expected_len

        for i in range(top_num):
            assert resp_json["leaderboard"][i]["rank"] == i + 1
            assert resp_json["leaderboard"][i]["username"] == user_data[i]["username"] 
        
        assert resp_json["leaderboard"][top_num]["rank"] == top_num + 2
        start_rank = resp_json["leaderboard"][top_num]["rank"]
        for i in range(top_num, expected_len):
            assert resp_json["leaderboard"][i]["rank"] == start_rank + i - top_num
            assert resp_json["leaderboard"][i]["username"] == user_data[user_idx - side_num + i - top_num]["username"]
        assert resp_json["leaderboard"][-1]["rank"] == top_num + 2 * side_num + 2

        # middle of pack
        user_idx = int(num_users / 2)
        response = client.get(
            "/stats/leaderboards/overall/volume", 
            headers=getHeaders(user_data[user_idx]["token"]),
            params=params,
        )
        assert response.status_code == 200
        resp_json = response.json()
        assert resp_json["fracture"] == top_num
        assert len(resp_json["leaderboard"]) == expected_len
        
        for i in range(top_num):
            assert resp_json["leaderboard"][i]["rank"] == i + 1
            assert resp_json["leaderboard"][i]["username"] == user_data[i]["username"]
        
        assert resp_json["leaderboard"][top_num]["rank"] == user_idx - side_num + 1
        start_rank = resp_json["leaderboard"][top_num]["rank"]
        for i in range(top_num, expected_len):
            assert resp_json["leaderboard"][i]["rank"] == start_rank + i - top_num
            assert resp_json["leaderboard"][i]["username"] == user_data[user_idx - side_num + i - top_num]["username"]
        assert resp_json["leaderboard"][-1]["rank"] == user_idx + side_num + 1

        # ranked just outside of final limit
        user_idx = num_users - side_num - 2
        response = client.get(
            "/stats/leaderboards/overall/volume", 
            headers=getHeaders(user_data[user_idx]["token"]),
            params=params,
        )
        assert response.status_code == 200
        resp_json = response.json()
        assert resp_json["fracture"] == top_num
        assert len(resp_json["leaderboard"]) == expected_len

        for i in range(top_num):
            assert resp_json["leaderboard"][i]["rank"] == i + 1
            assert resp_json["leaderboard"][i]["username"] == user_data[i]["username"] 

        assert resp_json["leaderboard"][top_num]["rank"] == num_users - 2 * side_num - 1
        start_rank = resp_json["leaderboard"][top_num]["rank"]
        for i in range(top_num, expected_len):
            assert resp_json["leaderboard"][i]["rank"] == start_rank + i - top_num
            assert resp_json["leaderboard"][i]["username"] == user_data[user_idx - side_num + i - top_num]["username"]
        assert resp_json["leaderboard"][-1]["rank"] == num_users - 1

        # ranked just inside of final limit
        user_idx = num_users - side_num - 1
        response = client.get(
            "/stats/leaderboards/overall/volume", 
            headers=getHeaders(user_data[user_idx]["token"]),
            params=params,
        )
        assert response.status_code == 200
        resp_json = response.json()
        assert resp_json["fracture"] == top_num
        assert len(resp_json["leaderboard"]) == expected_len

        for i in range(top_num):
            assert resp_json["leaderboard"][i]["rank"] == i + 1
            assert resp_json["leaderboard"][i]["username"] == user_data[i]["username"] 

        assert resp_json["leaderboard"][top_num]["rank"] == num_users - 2 * side_num
        start_rank = resp_json["leaderboard"][top_num]["rank"]
        for i in range(top_num, expected_len):
            assert resp_json["leaderboard"][i]["rank"] == start_rank + i - top_num
            assert resp_json["leaderboard"][i]["username"] == user_data[user_idx - side_num + i - top_num]["username"]
        assert resp_json["leaderboard"][-1]["rank"] == num_users

        # ranked last
        user_idx = num_users - 1
        response = client.get(
            "/stats/leaderboards/overall/volume", 
            headers=getHeaders(user_data[user_idx]["token"]),
            params=params,
        )
        assert response.status_code == 200
        resp_json = response.json()
        assert resp_json["fracture"] == top_num
        assert len(resp_json["leaderboard"]) == expected_len

        for i in range(top_num):
            assert resp_json["leaderboard"][i]["rank"] == i + 1
            assert resp_json["leaderboard"][i]["username"] == user_data[i]["username"] 

        assert resp_json["leaderboard"][top_num]["rank"] == num_users - 2 * side_num
        start_rank = resp_json["leaderboard"][top_num]["rank"]
        for i in range(top_num, expected_len):
            assert resp_json["leaderboard"][i]["rank"] == start_rank + i - top_num
            assert resp_json["leaderboard"][i]["username"] == user_data[num_users - (2 * side_num) + i - top_num - 1]["username"]

    except Exception as e:
        print(str(e))
        raise e
    finally:
        try:
            await conn.execute(
                """
                delete from users
                where is_verified = false
                """
            )
        except Exception: pass
        if conn: await conn.close()

def getHeaders(auth_token):
    return {
        "Authorization": f"Bearer {auth_token}"
    }