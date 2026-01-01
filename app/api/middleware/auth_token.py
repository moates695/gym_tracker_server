from datetime import datetime, timedelta, timezone
import jwt
import os
from dotenv import load_dotenv

load_dotenv(override=True)

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

if __name__ == "__main__":
   print(generate_token('moates695@gmail.com', '31fbaa9c-a0f2-45f5-835b-aa2d80d68892', days=1))
#    print(generate_token('moates695@gmail.com', 'df23687a-c71f-436d-b720-ea1ccd3ea977', days=1))