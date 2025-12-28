import json
import asyncio
import os
from fastapi.testclient import TestClient
from dotenv import load_dotenv
from uuid import uuid4
import requests
import random
from datetime import datetime, timedelta
import uuid

from ..main import app
from ..api.middleware.database import setup_connection
from ..tests.test_workout_save import build_workouts, save_workouts
from ..api.middleware.auth_token import generate_token
from ..api.middleware.misc import *

client = TestClient(app)

load_dotenv(override=True)

async def main():
    if input(f"Insert dummy data into {os.environ['ENVIRONMENT']}? [y/n] ") != 'y': return
    only_test_user = input(f"Update only test user data? [y/n] ") == 'y'
    try:
        conn = await setup_connection()

        # user_id = '31fbaa9c-a0f2-45f5-835b-aa2d80d68892'
        test_user_id = 'df23687a-c71f-436d-b720-ea1ccd3ea977'
        test_user_email = 'moates695@gmail.com'
        user_map = {
            test_user_id: generate_token(test_user_email, test_user_id, minutes=15)
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
                """, test_user_id
            )

        if not only_test_user:
            dummy_domain = "@dummydomain.com"
            await conn.execute(
                """
                delete
                from users
                where email like '%' || $1
                """, dummy_domain
            )

        if only_test_user:
            await conn.execute(
                """
                delete 
                from workouts w
                using users u
                where w.user_id = u.id
                and u.email = $1
                """, test_user_email
            )
        else:
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
                """, dummy_domain, test_user_email
            )

        server_base = os.environ['SERVER_ADDRESS']

        if not only_test_user:
            for _ in range(random.randint(20, 30)):
                try:
                    temp_email = f"{str(uuid4())}{dummy_domain}"
                    response = requests.post(
                        f"{server_base}/register/new",
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
                            "bodyfat": 15.0,
                            "send_email": False,
                        }
                    )
                    response.raise_for_status()
                    resp_json = response.json()
                    if resp_json["status"] != "success": 
                        raise Exception("register not successful")
                    temp_user_id = resp_json["user_id"]
                    # auth_token = generate_token(temp_email, temp_user_id, minutes=15)
                    temp_token = generate_token(temp_email, temp_user_id, minutes=30, is_temp=True)

                    code = await conn.fetchval(
                        """
                        select code
                        from user_codes
                        where user_id = $1 
                        """, temp_user_id
                    )

                    response = requests.get(
                        f"{server_base}/register/validate/receive",
                        headers={
                            "Authorization": f"Bearer {temp_token}"
                        },
                        params={
                            "code": code,
                        }
                    )
                    response.raise_for_status()
                    assert response.json()["status"] == "verified"
                    user_map[temp_user_id] = response.json()["auth_token"]
                
                except Exception as e:
                    print(e)
                    continue

        for user_id, token in user_map.items():
            workouts = await build_workouts(conn, 10, 20)

            if user_id == test_user_id:
                workouts += await build_workouts(conn, 5, 10, recent=True)

            await save_workouts(workouts, headers={
                "Authorization": f"Bearer {token}"
            }, skip_fail=True)

            for _ in range(20):
                await conn.execute(
                    """
                    insert into user_weights
                    (user_id, weight, created_at)
                    values
                    ($1, $2, $3)
                    """,
                    user_id,
                    random_weight(),
                    datetime.fromtimestamp(random_timestamp_ms() / 1000).replace(tzinfo=None)
                )

            for _ in range(10):
                await conn.execute(
                    """
                    insert into user_heights
                    (user_id, height, created_at)
                    values
                    ($1, $2, $3)
                    """,
                    user_id,
                    random.randint(130, 190),
                    datetime.fromtimestamp(random_timestamp_ms() / 1000).replace(tzinfo=None)
                )

        await conn.execute(
            """
            delete
            from friends
            where user1_id = $1
            or user2_id = $1
            """, test_user_id
        )

        user_id_rows = await conn.fetch(
            """
            select id
            from users
            where id != $1
            """, test_user_id
        )
        user_ids = [str(row["id"]) for row in user_id_rows]

        for user_id in user_ids:
            if random.random() < 0.25: continue
            await conn.execute(
                """
                insert into friends
                (user1_id, user2_id)
                values
                ($1, $2)
                """,
                test_user_id,
                user_id
            )
            await conn.execute(
                """
                insert into online_users
                (user_id, is_online)
                values
                ($1, $2)
                on conflict (user_id, is_online) 
                do update
                set is_online = $2
                """,
                user_id,
                random.random() < 0.5
            )



        await conn.execute(
            """
            update user_permissions
            set permission_value = 'public'
            where permission_key = 'searchable'
            """
        )

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