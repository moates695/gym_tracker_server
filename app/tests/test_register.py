from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
import jwt
import os
from uuid import uuid4
import pytest
import random

from ..main import app
from ..api.middleware.auth_token import decode_token, generate_token
from .conftest import get_auth_token, valid_user, get_code
from ..api.middleware.database import setup_connection

client = TestClient(app)

def test_valid_register(delete_users):
    response = client.post("/register/new", json=valid_user)
    assert response.status_code == 200
    assert "auth_token" not in response.json().keys()
    temp_token = response.json()["temp_token"]
    decode_token(temp_token, is_temp=True)

def test_email_taken(delete_users):
    user = valid_user.copy()

    response = client.post("/register/new", json=user)
    assert response.json()["status"] == "success"

    user["username"] = "testname2"
    user["email"] = user["email"].upper()

    response = client.post("/register/new", json=user)
    assert response.json()["status"] == "error"
    assert response.json()["fields"] == ["email"]

def test_username_taken(delete_users):
    user = valid_user.copy()

    response = client.post("/register/new", json=user)
    assert response.json()["status"] == "success"

    user["email"] = "test2@pytest.com"
    user["username"] = user["username"].upper()

    response = client.post("/register/new", json=user)
    assert response.json()["status"] == "error"
    assert response.json()["fields"] == ["username"]

@pytest.mark.asyncio
async def test_validate(delete_users):
    response = client.post("/register/new", json=valid_user)
    assert response.json()["status"] == "success"
    temp_token = response.json()["temp_token"]

    decoded_temp = decode_token(temp_token, is_temp=True)

    headers = {
        "Authorization": f"Bearer {temp_token}"
    }

    try:
        conn = await setup_connection()

        code = await get_code(decoded_temp["user_id"])

        while 1:
            bad_code = str(random.randint(100000,999999))
            if bad_code == code: continue
            break

        response = client.get("/register/validate/receive", 
            headers=headers,
            params={
                "code": bad_code,
            }
        )
        assert response.status_code == 200
        assert response.json()["status"] == "incorrect"

        response = client.get("/register/validate/receive", 
            headers=headers,
            params={
                "code": code,
            }
        )
        assert response.status_code == 200
        assert response.json()["status"] == "verified"
        assert "auth_token" in response.json()
        assert response.json()["user_data"] == {
            "user_id": decoded_temp["user_id"],
            "email": valid_user["email"],
            "username": valid_user["username"],
            "first_name": valid_user["first_name"],
            "last_name": valid_user["last_name"],
            "gender": valid_user["gender"],
            "goal_status": valid_user["goal_status"],
            "height": valid_user["height"],
            "ped_status": valid_user["ped_status"],
            "weight": valid_user["weight"],
        }

        response = client.get("/register/validate/receive", 
            headers=headers,
            params={
                "code": code,
            }
        )
        assert response.status_code == 200
        assert response.json()["status"] == "error"

        response = client.get("/register/validate/resend", 
            headers=headers,
            params={
                "send_email": False
            }
        )
        assert response.status_code == 200

        code1 = await get_code(decoded_temp["user_id"])

        response = client.get("/register/validate/resend", 
            headers=headers,
            params={
                "send_email": False
            }
        )
        assert response.status_code == 200

        code2 = await get_code(decoded_temp["user_id"])

        assert code1 != None and code2 != None
        assert code1 != code2

        response = client.get("/register/validate/receive", 
            headers=headers,
            params={
                "code": code1,
            }
        )
        assert response.status_code == 200
        assert response.json()["status"] == "incorrect"

        response = client.get("/register/validate/receive", 
            headers=headers,
            params={
                "code": code2,
            }
        )
        assert response.status_code == 200
        assert response.json()["status"] == "verified"

    except Exception as e:
        print(str(e))
        raise e
    finally:
        if conn: await conn.close()

def test_username_exists(delete_users):
    response = client.get("/register/check/username", params={
        "username": valid_user["username"]
    })
    assert response.status_code == 200
    assert response.json()["taken"] == False

    response = client.post("/register/new", json=valid_user)
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

@pytest.mark.asyncio
async def test_login(delete_users):
    response = client.post("/register/new", json=valid_user)
    assert response.status_code == 200
    temp_token = response.json()["temp_token"]
    decoded_temp = decode_token(temp_token, is_temp=True)

    auth_token = generate_token(
        decoded_temp["email"],
        decoded_temp["user_id"],
        minutes=30
    )

    response = client.get("/register/login", 
        headers={
            "Authorization": f"Bearer {auth_token}"
        },
        params={
            "send_email": False
        }
    )
    assert response.status_code == 200
    assert response.json()["account_state"] == "unverified"
    with pytest.raises(Exception):
        decode_token(response.json()["token"], is_temp=False)
    assert response.json()["user_data"] == None

    response = client.get("/register/validate/receive", 
        headers={
            "Authorization": f"Bearer {temp_token}"
        },
        params={
            "code": await get_code(decode_token(temp_token, is_temp=True)["user_id"])
        }
    )
    assert response.status_code == 200
    assert response.json()["status"] == "verified"

    response = client.get("/register/login", 
        headers={
            "Authorization": f"Bearer {auth_token}"
        },
        params={
            "send_email": False
        }
    )
    assert response.status_code == 200
    assert response.json()["account_state"] == "good"
    assert response.json()["user_data"] == {
        "user_id": decode_token(response.json()["token"])["user_id"],
        "email": valid_user["email"],
        "username": valid_user["username"],
        "first_name": valid_user["first_name"],
        "last_name": valid_user["last_name"],
        "gender": valid_user["gender"],
        "goal_status": valid_user["goal_status"],
        "height": valid_user["height"],
        "ped_status": valid_user["ped_status"],
        "weight": valid_user["weight"],
    }

    response = client.get("/register/login", 
        headers={
            "Authorization": f"Bearer {auth_token}"
        },
        params={
            "send_email": False
        }
    )
    assert response.status_code == 200
    assert response.json()["account_state"] == "good"

@pytest.mark.asyncio
async def test_sign_in(delete_users):
    user = valid_user.copy()

    response = client.post("/register/new", json=valid_user)
    assert response.status_code == 200

    response = client.post("/register/sign-in", json={
        "email": user["email"],
        "password": user["password"],
        "send_email": False
    })
    assert response.json()["status"] == "good"
    temp_token = response.json()["temp_token"]
    decode_token(temp_token, is_temp=True)

    response = client.get("/register/validate/receive", 
        headers={
            "Authorization": f"Bearer {temp_token}"
        },
        params={
            "code": await get_code(decode_token(temp_token, is_temp=True)["user_id"])
        }
    )
    assert response.status_code == 200
    assert response.json()["status"] == "verified"

    response = client.post("/register/sign-in", json={
        "email": user["email"],
        "password": user["password"],
        "send_email": False
    })
    response = client.post("/register/sign-in", json={
        "email": user["email"],
        "password": user["password"],
        "send_email": False
    })
    assert response.json()["status"] == "good"
    temp_token = response.json()["temp_token"]
    decode_token(temp_token, is_temp=True)

    response = client.post("/register/sign-in", json={
        "email": user["email"],
        "password": "incorrect",
        "send_email": False
    })
    assert response.json()["status"] == "incorrect-password"
    assert response.json()["temp_token"] == None

    response = client.post("/register/sign-in", json={
        "email": "not@email.com",
        "password":  user["password"],
        "send_email": False
    })
    assert response.json()["status"] == "none"
    assert response.json()["temp_token"] == None


