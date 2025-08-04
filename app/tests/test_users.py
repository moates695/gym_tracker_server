from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
import jwt
import os
from uuid import uuid4
import random

from ..main import app
from ..api.middleware.token import decode_token, generate_token
from ..tests.test_register import valid_user

client = TestClient(app)

def test_users_data_update(delete_test_users, create_user):
    auth_token = create_user

    user = valid_user.copy()

    headers = {
        "Authorization": f"Bearer {auth_token}"
    }

    for _ in range(random.randint(3,5)):
        options = {
            "first_name": str(uuid4()),
            "last_name": str(uuid4()),
            "gender": random.choice(['male','female','other']),
            "height": random.randint(20,200) + random.random(),
            "weight": random.randint(20,200) + random.random(),
            "goal_status": random.choice(['bulking','cutting','maintaining']),
            "ped_status":  random.choice(["natural","juicing","silent"]),
        }
        remaining_keys = list(options.keys())
        body = {}
        for _ in range(random.randint(1, len(options.keys()) - 1)):
            key = random.choice(remaining_keys)
            body[key] = options[key]
            remaining_keys.remove   

        user.update(body)

        response = client.put("/users/data/update", json=body, headers=headers)
        assert response.status_code == 200

        response = client.get("/users/data/get", headers=headers)
        assert response.status_code == 200
        user_data = response.json()["user_data"]
        for key in options:
            if type(user[key]) != float:
                assert user[key] == user_data[key]
            else:
                assert round(user[key], 3) == round(user_data[key], 3)

