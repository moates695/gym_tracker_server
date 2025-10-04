import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import pytest_asyncio
import pytest
from fastapi.testclient import TestClient

from app.api.middleware.database import setup_connection, load_env_vars
from ..main import app
from ..tests.test_register import valid_user

load_env_vars()

def pytest_configure(config):
    if os.getenv('ENVIRONMENT') != 'prod': return
    pytest.exit("Tests cannot run in production environment", returncode=1)

@pytest.fixture(scope="session", autouse=True)
def patch_env():
    old_val = os.environ.get("ENVIRONMENT")
    os.environ["ENVIRONMENT"] = "pytest"
    yield
    os.environ["ENVIRONMENT"] = old_val

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
    return response.json()["auth_token"]


