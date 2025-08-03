from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
import jwt
import os
from uuid import uuid4

from ..main import app
from ..api.middleware.token import decode_token

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
    assert response.status_code == 200

    user["username"] = "testname2"
    user["email"] = user["email"].upper()

    response = client.post("/register", json=user)
    assert response.status_code == 400

def test_username_taken(delete_test_users):
    user = valid_user.copy()

    response = client.post("/register", json=user)
    assert response.status_code == 200

    user["email"] = "test2@pytest.com"
    user["username"] = user["username"].upper()

    response = client.post("/register", json=user)
    assert response.status_code == 400

def test_validate(delete_test_users):
    response = client.post("/register", json=valid_user)
    assert response.status_code == 200

    params = get_validate_params(valid_user["email"])

    response = client.get("/register/validate/receive", params=params)
    assert response.status_code == 200

    response = client.get("/register/validate/receive", params=params)
    assert response.status_code == 400

def test_validate_email_not_exist(delete_test_users):
    params = get_validate_params(valid_user["email"])

    response = client.get("/register/validate/receive", params=params)
    assert response.status_code == 400

    response = client.post("/register", json=valid_user)
    assert response.status_code == 200

    response = client.get("/register/validate/receive", params=params)
    assert response.status_code == 200

def test_validate_past_expiry(delete_test_users):
    params = get_validate_params(valid_user["email"], 0)

    response = client.post("/register", json=valid_user)
    assert response.status_code == 200

    response = client.get("/register/validate/receive", params=params)
    assert response.status_code == 400

def get_validate_params(email: str, expiry_mins=15):
    payload = {
        "email": email,
        "exp": (datetime.now(timezone.utc) + timedelta(minutes=expiry_mins)).timestamp()
    }
    token = jwt.encode(payload, os.getenv("SECRET_KEY"), algorithm="HS256")
    return {
        "token": token
    }

def test_username_exists(delete_test_users):
    response = client.get("/register/username", params={
        "username": valid_user["username"]
    })
    assert response.status_code == 200
    assert response.json()["taken"] == False

    response = client.post("/register", json=valid_user)
    assert response.status_code == 200

    response = client.get("/register/username", params={
        "username": valid_user["username"]
    })
    assert response.status_code == 200
    assert response.json()["taken"] == True

    response = client.get("/register/username", params={
        "username": valid_user["username"].upper()
    })
    assert response.status_code == 200
    assert response.json()["taken"] == True

def test_is_validated(delete_test_users):
    response = client.get("/register/validate/check", params={
        "email": valid_user["email"],
        "user_id": str(uuid4())
    })
    assert response.status_code == 200
    assert response.json()["account_state"] == "none"
    assert response.json()["auth_token"] == None

    response = client.post("/register", json=valid_user)
    assert response.status_code == 200

    response = client.get("/register/validate/check", params={
        "email": valid_user["email"],
        "user_id": str(uuid4())
    })
    assert response.status_code == 200
    assert response.json()["account_state"] == "unverified"
    assert response.json()["auth_token"] == None

    params = get_validate_params(valid_user["email"])

    response = client.get("/register/validate/receive", params=params)
    assert response.status_code == 200

    response = client.get("/register/validate/check", params={
        "email": valid_user["email"],
        "user_id": str(uuid4())
    })
    assert response.status_code == 200
    assert response.json()["account_state"] == "good"
    assert "auth_token" in response.json().keys()
    jwt.decode(response.json()["auth_token"], os.getenv("SECRET_KEY"), algorithms=["HS256"])

    response = client.get("/register/validate/check", params={
        "email": valid_user["email"].upper(),
        "user_id": str(uuid4())
    })
    assert response.status_code == 200
    assert response.json()["account_state"] == "good"