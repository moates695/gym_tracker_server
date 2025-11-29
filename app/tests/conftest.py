import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import pytest_asyncio
import pytest
from fastapi.testclient import TestClient
from dotenv import load_dotenv 

from app.api.middleware.database import setup_connection
from ..main import app
from app.api.middleware.auth_token import decode_token, generate_token

load_dotenv(override=True)

def pytest_configure(config):
    if os.getenv("ENVIRONMENT") == "pytest": return
    pytest.exit("Tests can only run when ENVIRONMENT=pytest", returncode=1)

@pytest_asyncio.fixture(scope="function")
async def delete_users():
    await _delete_users()
    yield
    await _delete_users()

async def _delete_users():
    try:
        conn = await setup_connection()

        await conn.execute(
            """
            delete
            from users;
            """
        )

    except Exception as e:
        raise Exception(f"Error in fixture: {e}")
    finally:
        if conn: await conn.close()

@pytest.fixture
def create_user():
    client = TestClient(app)

    response = client.post("/register/new", json=valid_user)
    assert response.status_code == 200
    temp_token = response.json()["temp_token"]
    
    auth_token = get_auth_token(temp_token)
    response = client.get("/register/validate/receive", params={
        "token": auth_token
    })
    assert response.status_code == 200

    response = client.get("/register/validate/check", headers={
        "Authorization": f"Bearer {temp_token}"
    })
    assert response.status_code == 200
    return response.json()["auth_token"]

def get_auth_token(temp_token):
    decoded_temp = decode_token(temp_token, is_temp=True)
    return generate_token(
        decoded_temp["email"],
        decoded_temp["user_id"],
        minutes=30
    )

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
    "date_of_birth": "2001-09-11",
    "send_email": False
}