import pytest
from fastapi.testclient import TestClient
import jwt
import os
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from ..main import app
from ..api.middleware.auth_token import generate_token

client = TestClient(app)

def test_verify_token(delete_users):
    response = client.get("/protected")
    assert response.status_code == 403
    response = client.get("/protected_temp")
    assert response.status_code == 403

    auth_token = generate_token(
        "test@pytest.com", 
        str(uuid4()),
        minutes=1
    )
    headers = {
        "Authorization": f"Bearer {auth_token}"
    }
    response = client.get("/protected", headers=headers)
    assert response.status_code == 200
    response = client.get("/protected_temp", headers=headers)
    assert response.status_code == 401
    
    temp_token = generate_token(
        "test@pytest.com", 
        str(uuid4()),
        minutes=1,
        is_temp=True
    )
    headers = {
        "Authorization": f"Bearer {temp_token}"
    }
    response = client.get("/protected", headers=headers)
    assert response.status_code == 401
    response = client.get("/protected_temp", headers=headers)
    assert response.status_code == 200

    token = get_bad_token
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = client.get("/protected", headers=headers)
    assert response.status_code == 401
    response = client.get("/protected_temp", headers=headers)
    assert response.status_code == 401


#####################

def get_bad_token():
    utc_now = datetime.now(timezone.utc)
    payload = {
        "email": "test@pytest.com",
        "user_id": str(uuid4()),
        "exp": (utc_now + timedelta(minutes=1)).timestamp(),
        "iat": utc_now.timestamp()
    }
    return jwt.encode(payload, "bad-key", algorithm="HS256")