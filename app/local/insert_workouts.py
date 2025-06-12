import requests
from datetime import datetime, timezone, timedelta
import random
import asyncio

from ..api.middleware.database import setup_connection
from ..api.middleware.token import generate_token

async def main():
    day_secs = 24 * 60 * 60 
    # time_deltas = [
    #     0, 1, 2, 4, 7, 8, 10, 15, 20, 25, 40, 50, 70, 150, 170, 300, 364, 370 
    # ]
    time_deltas = [random.randint(1, 100) for _ in range(60)]
    for time_delta in time_deltas:
        await save_workout(time_delta * day_secs)

async def save_workout(time_delta):
    try:
        conn = await setup_connection()

        exercise_id_rows = await conn.fetch(
            """
            select id, is_body_weight
            from exercises
            """
        )

        exercise_ids = [str(e["id"]) for e in exercise_id_rows]
        body_weight_map = {str(e["id"]): e["is_body_weight"] for e in exercise_id_rows}

    except Exception as e:
        print(e)
    finally:
        if conn: await conn.close()


    user_id = 'a8bf1a23-33f0-4b52-9d9b-7bfde7eea36a'
    user_email = "moates695@gmail.com"

    exercises = []
    for _ in range(random.randint(3,6)):
        exercise_id = random.choice(exercise_ids) 
        exercises.append({
            "id": exercise_id,
            "set_data": [
                {
                    "reps": random.randint(5,15),
                    "weight": random.random() * 120,
                    "num_sets": random.randint(1,5)
                }
            ],
            "is_body_weight": body_weight_map[exercise_id]
        })

    response = requests.post(
        "http://127.0.0.1:8000/workout/save",
        json={
            "exercises": exercises,
            "duration": random.randint(45, 120) * 1000,
            "start_time": (int(datetime.now(timezone.utc).timestamp()) - time_delta) * 1000
        },
        headers={
            "Authorization": f"Bearer {generate_token(user_email, user_id, minutes=5)}"
        }
    )
    response. raise_for_status()

    # resp = await workout_save(req, {})
    # print(resp)

    # requests.post(
    #     "http://127.0.0.1:8000//workout/save",
    #     json={
    #         "exercises": [
    #             {
    #                 "id": "",
    #                 "set_data": [
    #                     {
    #                         "reps": 3,
    #                         "weight": 105,
    #                         "num_sets": 3
    #                     }
    #                 ],
    #                 "is_body_weight": True
    #             }
    #         ],
    #         "start_time": datetime.now(timezone.utc) - timedelta(days=2),
    #         "duration": 1800
    #     }
    # )

if __name__ == "__main__":
    asyncio.run(main())