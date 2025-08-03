import pytest
import jwt
import os
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from ..api.middleware.token import generate_token, decode_token

def test_generate_token():
    email = "test@pytest.com"
    user_id = str(uuid4())
    days = 2
    minutes = 60
    token = generate_token(
        email,
        user_id,
        days=days,
        minutes=minutes,
    )
    decoded = decode_token(token)

    with pytest.raises(Exception):
        decode_token(token, is_temp=True)

    utc_now = datetime.now(timezone.utc)
    delta = timedelta(days=days, minutes=minutes)
    room_delta = timedelta(seconds=10)

    assert decoded["email"] == email
    assert decoded["user_id"] == user_id
    assert decoded["exp"] < (utc_now + delta + room_delta).timestamp()
    assert decoded["exp"] > (utc_now + delta - room_delta).timestamp()

    token = generate_token(
        email,
        user_id,
        days=days,
        minutes=minutes,
        is_temp=True
    )
    decode_token(token, is_temp=True)

    with pytest.raises(Exception):
        decode_token(token)