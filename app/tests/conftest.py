import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

import pytest_asyncio
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from api.middleware.database import setup_connection
from ..main import app
from ..tests.test_register import valid_user

load_dotenv()

@pytest_asyncio.fixture(scope="function")
async def delete_test_users():
    await _delete_test_users()
    yield
    await _delete_test_users()

async def _delete_test_users():
    try:
        conn = await setup_connection()

        await conn.execute(
            """
            delete
            from users
            where lower(email) like '%@pytest.com';
            """
        )

    except Exception as e:
        raise Exception(f"Error in fixture: {e}")
    finally:
        if conn: await conn.close()

@pytest.fixture
def create_user():
    client = TestClient(app)

    response = client.post("/register", json=valid_user)
    temp_token = response.json()["temp_token"]
    
    response = client.get("/register/validate/receive", params={
        "token": temp_token
    })

    response = client.get("/register/validate/check", headers={
        "Authorization": f"Bearer {temp_token}"
    })
    return response.json()["auth_token"]
