from datetime import datetime, timedelta, timezone
import jwt
import os

def generate_token(email, user_id, days=0, minutes=0):
    utc_now = datetime.now(timezone.utc)
    payload = {
        "email": email,
        "user_id": str(user_id),
        "exp": (utc_now + timedelta(days=days, minutes=minutes)).timestamp(),
        "iat": utc_now.timestamp()
    }
    return jwt.encode(payload, os.getenv("SECRET_KEY"), algorithm="HS256")

def decode_token(token):
    try:
        return jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=["HS256"])
    except Exception as e:
        return None

def is_token_expired(token):
    return datetime.now(timezone.utc) > datetime.fromtimestamp(token["exp"], timezone.utc)