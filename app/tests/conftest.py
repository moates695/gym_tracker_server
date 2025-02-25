import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

import pytest

from api.middleware.database import setup_connection

@pytest.fixture
def delete_test_users():
    _delete_test_users()
    yield
    _delete_test_users()

def _delete_test_users():
    try:
        conn, cur = setup_connection()

        cur.execute("""
delete
from users
where lower(email) like '%@pytest.com'""")
        conn.commit()

    except Exception as e:
        raise Exception(f"Error in fixture: {e}")
    finally:
        if cur: cur.close()
        if conn: conn.close()