from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
import jwt
import os
from uuid import uuid4
import random

from ..main import app
from ..api.middleware.auth_token import decode_token, generate_token
from ..tests.test_register import valid_user

client = TestClient(app)

def test_users_data_update(delete_users, create_user):
    auth_token = create_user

    headers = {
        "Authorization": f"Bearer {auth_token}"
    }

    response = client.get("/users/data/get", headers=headers)
    assert response.status_code == 200
    user_data = response.json()["user_data"]

    for _ in range(random.randint(20,30)):
        options = {
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

        user_data.update(body)

        response = client.post("/users/data/update", json=body, headers=headers)
        assert response.status_code == 200

        response = client.get("/users/data/get", headers=headers)
        assert response.status_code == 200
        resp_user_data = response.json()["user_data"]
        for key in options:
            if type(user_data[key]) != float:
                assert user_data[key] == resp_user_data[key]
            else:
                assert round(user_data[key], 2) == round(resp_user_data[key], 2)


def test_users_data_history(delete_users, create_user):
    auth_token = create_user

    user = valid_user.copy()
    user_data_history = {
        "height": [user["height"]],
        "weight": [user["weight"]],
        "goal_status": [user["goal_status"]],
        "ped_status": [user["ped_status"]]
    }

    headers = {
        "Authorization": f"Bearer {auth_token}"
    }

    num_calls = random.randint(20,30)
    for _ in range(num_calls):
        options = {
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
        for key, value in body.items():
            # assert user[key] == options[key]
            user_data_history[key].append(value)

        response = client.post("/users/data/update", json=body, headers=headers)
        assert response.status_code == 200

    response = client.get("/users/data/get/history", headers=headers)
    assert response.status_code == 200
    response_data_history = response.json()["data_history"]

    for key in user_data_history.keys():
        user_data_history[key].reverse()
        assert len(user_data_history[key]) == len(response_data_history[key])
        for i in range(len(user_data_history[key])):
            local_value = user_data_history[key][i]
            response_value = response_data_history[key][i]["value"]
            if type(local_value) == float:
                assert round(local_value, 2) == round(response_value, 2)
            else:
                assert local_value == response_value


