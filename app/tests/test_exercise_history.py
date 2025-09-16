from fastapi.testclient import TestClient

from ..main import app
from ..api.middleware.auth_token import decode_token
 

client = TestClient(app)

def test_exercise_history(delete_test_users, create_user):
    auth_token = create_user
    decoded_auth_token = decode_token(auth_token)
    user_id = decoded_auth_token["user_id"]

