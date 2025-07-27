from datetime import datetime, timedelta, timezone
import jwt
import os

def generate_token(email, user_id, days=0, minutes=0, is_temp=False):
    utc_now = datetime.now(timezone.utc)
    payload = {
        "email": email,
        "user_id": str(user_id),
        "exp": (utc_now + timedelta(days=days, minutes=minutes)).timestamp(),
        "iat": utc_now.timestamp()
    }
    return jwt.encode(payload, get_env_value(is_temp), algorithm="HS256")

def decode_token(token, is_temp=False):
    return jwt.decode(token, get_env_value(is_temp), algorithms=["HS256"])

def is_token_expired(token):
    return datetime.now(timezone.utc) > datetime.fromtimestamp(token["exp"], timezone.utc)

def get_env_value(is_temp):
    return os.getenv("SECRET_KEY" if not is_temp else "TEMP_SECRET_KEY")