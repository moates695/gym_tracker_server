import json
import asyncio
import os
from fastapi.testclient import TestClient
from dotenv import load_dotenv
from uuid import uuid4
import requests
import random
from datetime import datetime, timedelta

from ..main import app
from ..api.middleware.database import setup_connection
from ..tests.test_workout_save import build_workouts, save_workouts
from ..api.middleware.auth_token import generate_token

client = TestClient(app)

load_dotenv(override=True)

async def main():
    try:
        conn = await setup_connection()

        user_id = '31fbaa9c-a0f2-45f5-835b-aa2d80d68892'
        user_email = 'moates695@gmail.com'
        user_map = {
            user_id: generate_token(user_email, user_id, minutes=15)
        }

        tables = [
            'overall_leaderboard',
            'workout_totals',
            'workout_muscle_group_totals',
            'workout_muscle_target_totals'
        ]
        for table in tables:
            await conn.execute(
                f"""
                delete
                from {table}
                where user_id = $1
                """, user_id
            )

        dummy_domain = "@dummydomain.com"
        await conn.execute(
            """
            delete
            from users
            where email like '%' || $1
            """, dummy_domain
        )

        await conn.execute(
            """
            delete 
            from workouts w
            using users u
            where w.user_id = u.id
            and (
                u.email like '%' || $1
                or 
                u.email = $2
            )
            """, dummy_domain, user_email
        )

        server_base = os.environ['SERVER_ADDRESS']

        for _ in range(random.randint(20, 30)):
            try:
                temp_email = f"{str(uuid4())}{dummy_domain}"
                response = requests.post(
                    f"{server_base}/register",
                    json={
                        "email": temp_email,
                        "password": "Password1!",
                        "username": str(uuid4())[:20],
                        "first_name": "",
                        "last_name": "",
                        "gender": random.choice(["male", "female", "other"]),
                        "height": random.randint(130, 210),
                        "weight": random.randint(50, 130),
                        "goal_status": random.choice(["bulking", "cutting", "maintaining"]),
                        "ped_status": random.choice(["natural", "juicing", "silent"]),
                        "date_of_birth": pick_date(),
                        "send_email": False,
                    }
                )
                response.raise_for_status()
                resp_json = response.json()
                if resp_json["status"] != "success": 
                    raise Exception("register not successful")
                temp_user_id = resp_json["user_id"]
                temp_token = generate_token(temp_email, temp_user_id, minutes=15, is_temp=True)

                response = requests.get(
                    f"{server_base}/register/validate/receive",
                    params={
                        "token": temp_token
                    }
                )
                response.raise_for_status()
                
                response = requests.get(
                    f"{server_base}/register/validate/check",
                    headers=get_headers(temp_token)
                )
                response.raise_for_status()
                resp_json = response.json()
                if resp_json["account_state"] != "good":
                    raise Exception("account state not good")

                user_map[temp_user_id] = resp_json["auth_token"]
            
            except Exception as e:
                print(e)
                continue

        for user_id, token in user_map.items():
            workouts = await build_workouts(conn, 10, 20)
            await save_workouts(workouts, headers={
                "Authorization": f"Bearer {token}"
            }, skip_fail=True)

    except Exception as e:
        raise e
    finally:
        if conn: await conn.close()

def get_headers(token: str):
    return {
        "Authorization": f"Bearer {token}"
    }

def pick_date():
    start_date = datetime(1970, 1, 1)
    end_date = datetime(2009, 12, 31)
    delta_days = (end_date - start_date).days
    random_days = random.randint(0, delta_days)
    random_date = start_date + timedelta(days=random_days)
    return  random_date.strftime("%Y-%m-%d")

if __name__ == "__main__":
    asyncio.run(main())