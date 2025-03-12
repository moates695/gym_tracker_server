from datetime import datetime, timedelta, timezone
import jwt
import os

def generate_token(email, days=0, minutes=0):
    payload = {
        "email": email,
        "expiry": (datetime.now(timezone.utc) + timedelta(days=days, minutes=minutes)).timestamp(),
        "days": days,
        "minutes": minutes
    }
    return jwt.encode(payload, os.getenv("SECRET_KEY"), algorithm="HS256")

def decode_token(token):
    return jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=["HS256"])

def is_token_expired(token):
    return datetime.now(timezone.utc) > datetime.fromtimestamp(token["expiry"], timezone.utc)