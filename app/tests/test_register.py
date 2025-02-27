from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
import jwt
import os 

from ..main import app

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
    "send_email": False
}

def test_valid_register(delete_test_users):
    response = client.post("/register", json=valid_user)
    assert response.status_code == 200

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

    payload = {
        "email": valid_user["email"],
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15)
    }
    token = jwt.encode(payload, os.getenv("SECRET_KEY"), algorithm="HS256")
    params = {
        "token": token
    }

    response = client.get("/register/validate/receive", params=params)
    assert response.status_code == 200