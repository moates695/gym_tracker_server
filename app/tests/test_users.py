from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
import jwt
import os
from uuid import uuid4

from ..main import app
from ..api.middleware.token import decode_token, generate_token
from ..tests.test_register import valid_user

client = TestClient(app)

def test_users_data_update(delete_test_users):
    # todo: fixture or helper that registers and verifies a user
    pass