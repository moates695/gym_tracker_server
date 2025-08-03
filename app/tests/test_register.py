from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
import jwt
import os
from uuid import uuid4

from ..main import app
from ..api.middleware.token import decode_token, generate_token

client = TestClient(app)

valid_user = {
    "email": "test@pytest.com",
    "password": "Password1!",
    "username": "testname",
    "first_name": "John",
    "last_name": "Doe",
    "gender": "male",
    "height": 183,
    "weight": 98,
    "goal_status": "cutting",
    "ped_status": 'natural',
    "send_email": False
}

def test_valid_register(delete_test_users):
    response = client.post("/register", json=valid_user)
    assert response.status_code == 200
    assert "auth_token" not in response.json().keys()
    temp_token = response.json()["temp_token"]
    decode_token(temp_token, is_temp=True)

def test_email_taken(delete_test_users):
    user = valid_user.copy()

    response = client.post("/register", json=user)
    assert response.json()["status"] == "success"

    user["username"] = "testname2"
    user["email"] = user["email"].upper()

    response = client.post("/register", json=user)
    assert response.json()["status"] == "error"
    assert response.json()["fields"] == ["email"]

def test_username_taken(delete_test_users):
    user = valid_user.copy()

    response = client.post("/register", json=user)
    assert response.json()["status"] == "success"

    user["email"] = "test2@pytest.com"
    user["username"] = user["username"].upper()

    response = client.post("/register", json=user)
    assert response.json()["status"] == "error"
    assert response.json()["fields"] == ["username"]

def test_validate(delete_test_users):
    response = client.post("/register", json=valid_user)
    assert response.json()["status"] == "success"
    temp_token = response.json()["temp_token"]

    params = {
        "token": temp_token
    }

    response = client.get("/register/validate/receive", params=params)
    assert response.status_code == 200

    response = client.get("/register/validate/receive", params=params)
    assert response.status_code == 400

def test_validate_past_expiry(delete_test_users):
    response = client.post("/register", json=valid_user)
    assert response.status_code == 200
    temp_token = response.json()["temp_token"]
    decoded = decode_token(temp_token, is_temp=True)

    expired_token = generate_token(
        valid_user["email"],
        decoded["user_id"],
        minutes=0,
        is_temp=True
    )

    params = {
        "token": expired_token
    }

    response = client.get("/register/validate/receive", params=params)
    assert response.status_code == 401

def test_username_exists(delete_test_users):
    response = client.get("/register/check/username", params={
        "username": valid_user["username"]
    })
    assert response.status_code == 200
    assert response.json()["taken"] == False

    response = client.post("/register", json=valid_user)
    assert response.status_code == 200

    response = client.get("/register/check/username", params={
        "username": valid_user["username"]
    })
    assert response.status_code == 200
    assert response.json()["taken"] == True

    response = client.get("/register/check/username", params={
        "username": valid_user["username"].upper()
    })
    assert response.status_code == 200
    assert response.json()["taken"] == True

def test_is_validated(delete_test_users):
    response = client.post("/register", json=valid_user)
    assert response.status_code == 200
    temp_token = response.json()["temp_token"]

    headers = {
        "Authorization": f"Bearer {temp_token}"
    }

    response = client.get("/register/validate/check", headers=headers)
    assert response.status_code == 200
    assert response.json()["account_state"] == "unverified"
    assert response.json()["auth_token"] == None

    response = client.get("/register/validate/receive", params={
        "token": temp_token
    })
    assert response.status_code == 200

    response = client.get("/register/validate/check", headers=headers)
    assert response.status_code == 200
    assert response.json()["account_state"] == "good"
    decode_token(response.json()["auth_token"])

    invalid_token = generate_token(
        "invalid",
        str(uuid4()),
        minutes=1,
        is_temp=True
    )
    response = client.get("/register/validate/check", headers={
        "Authorization": f"Bearer {invalid_token}"
    })
    assert response.status_code == 200
    assert response.json()["account_state"] == "none"

def test_login(delete_test_users):
    response = client.post("/register", json=valid_user)
    assert response.status_code == 200
    temp_token = response.json()["temp_token"]

    response = client.get("/register/validate/receive", params={
        "token": temp_token
    })
    assert response.status_code == 200

    response = client.get("/register/validate/check", headers={
        "Authorization": f"Bearer {temp_token}"
    })
    assert response.status_code == 200
    assert response.json()["account_state"] == "good"
    auth_token = response.json()["auth_token"]
    decode_token(auth_token)

    response = client.get("/login", headers={
        "Authorization": f"Bearer {auth_token}"
    })
    assert response.status_code == 200
    assert response.json()["account_state"] == "good"
    decode_token(response.json()["auth_token"])

def test_sign_in(delete_test_users):
    user = valid_user.copy()

    response = client.post("/register", json=valid_user)
    assert response.status_code == 200
    temp_token = response.json()["temp_token"]

    response = client.post("/sign-in", json={
        "email": user["email"],
        "password": user["password"]
    })
    assert response.json()["status"] == "unverified"
    decode_token(response.json()["token"], is_temp=True)

    response = client.get("/register/validate/receive", params={
        "token": temp_token
    })
    assert response.status_code == 200

    response = client.post("/sign-in", json={
        "email": user["email"],
        "password": user["password"]
    })
    assert response.json()["status"] == "signed-in"
    decode_token(response.json()["token"])

    response = client.post("/sign-in", json={
        "email": user["email"],
        "password": "incorrect"
    })
    assert response.json()["status"] == "incorrect-password"
    assert response.json()["token"] == None

    response = client.post("/sign-in", json={
        "email": "not@email.com",
        "password":  user["password"]
    })
    assert response.json()["status"] == "none"
    assert response.json()["token"] == None

