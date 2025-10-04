import pytest
from fastapi.testclient import TestClient
from copy import deepcopy
import json
from datetime import datetime, timezone, timedelta
import math
from uuid import uuid4

from ..main import app
from ..api.middleware.auth_token import decode_token, generate_token
from ..tests.test_workout_save import build_workouts, save_workouts
from ..api.middleware.database import setup_connection
from ..api.middleware.misc import datetime_to_timestamp_ms
from ..api.routes.exercises import timespan_to_ms
from ..tests.test_register import valid_user

client = TestClient(app)

@pytest.mark.asyncio
async def test_overall_volume(delete_test_users):
    
    top_num = 10
    side_num = 20
    params = {
        "top_num": top_num,
        "side_num": side_num
    }
    length = top_num + 2 * side_num + 1

    try:
        conn = await setup_connection()

        curr_max_volume = await conn.fetchval(
            """
            select max(volume)
            from volume_leaderboard
            """
        )

        user_data = []
        for i in range(2 * length):
            email = str(uuid4())
            user_id = await conn.fetchval(
                """
                insert into users
                (email, password, username, first_name, last_name, gender)
                values
                ($1, $2, $3, $4, $5, $6)
                returning id
                """, email, str(uuid4()), str(uuid4()), str(uuid4()), str(uuid4()), 'male'
            )
            user_data.append({
                "user_id": user_id,
                "email": email,
                "token": generate_token(email, user_id, minutes=5)
            })

            await conn.execute(
                """
                insert into volume_leaderboard
                (user_id, volume, last_updated)
                values
                ($1, $2, $3)
                """, user_id, curr_max_volume + i + 10, datetime.now(tz=timezone.utc).replace(tzinfo=None)
            )

        response = client.get(
            "/stats/leaderboards/overall/volume", 
            headers=getHeaders(user_data[-1]["token"]),
            params=params,
        )
        assert response.status_code == 200
        resp_json = response.json()
        assert resp_json["fracture"] is None
        assert len(resp_json["leaderboard"]) == length
        for i in range(length):
            assert resp_json["leaderboard"][i]["rank"] == i + 1

        response = client.get(
            "/stats/leaderboards/overall/volume", 
            headers=getHeaders(user_data[int(length / 2)]["token"]),
            params=params,
        )
        assert response.status_code == 200
        resp_json = response.json()
        assert resp_json["fracture"] == top_num
        assert len(resp_json["leaderboard"]) == length
        
        for i in range(top_num):
            assert resp_json["leaderboard"][i]["rank"] == i + 1
        
        start_idx = top_num
        start_rank = resp_json["leaderboard"][start_idx]["rank"]
        for i in range(start_idx, length):
            assert resp_json["leaderboard"][i]["rank"] == start_rank + i - start_idx

        response = client.get(
            "/stats/leaderboards/overall/volume", 
            headers=getHeaders(user_data[0]["token"]),
            params=params,
        )
        assert response.status_code == 200
        resp_json = response.json()
        assert resp_json["fracture"] == top_num
        assert len(resp_json["leaderboard"]) == length

        for i in range(top_num):
            assert resp_json["leaderboard"][i]["rank"] == i + 1

        start_idx = top_num
        start_rank = resp_json["leaderboard"][start_idx]["rank"]
        for i in range(start_idx, length):
            assert resp_json["leaderboard"][i]["rank"] == start_rank + i - start_idx
        
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