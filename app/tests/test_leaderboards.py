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
async def test_overall_volume(delete_test_users, create_user):
    auth_token = create_user

    # headers = {
    #     "Authorization": f"Bearer {auth_token}"
    # }
    params = {
        "top_num": 10,
        "side_num": 20
    }

    try:
        conn = await setup_connection()

        curr_max_volume = await conn.fetchval(
            """
            select max(volume)
            from volume_leaderboard
            """
        )

        user_data = []
        for i in range(100):
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
                """, user_id, curr_max_volume + i + 1, datetime.now(tz=timezone.utc).replace(tzinfo=None)
            )

        response = client.get(
            "/stats/leaderboards/overall/volume", 
            headers=getHeaders(user_data[-1]["token"]),
            params=params,
        )
        assert response.status_code == 200
        resp_json = response.json()
        assert resp_json["fracture"] is None
        assert len(resp_json["leaderboard"]) == 51
        # for i in range()

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