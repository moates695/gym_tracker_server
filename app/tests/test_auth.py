import pytest
from fastapi.testclient import TestClient
import jwt
import os

from ..main import app

client = TestClient(app)

def test_verify_token():
    payload = {
        "email": "test@pytest.com"
    }
    token = jwt.encode(payload, os.getenv("SECRET_KEY"), algorithm="HS256")
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = client.get("/protected", headers=headers)
    assert response.status_code == 200

    token = jwt.encode(payload, "invalid-key", algorithm="HS256")
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = client.get("/protected", headers=headers)
    assert response.status_code == 401
