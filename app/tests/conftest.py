import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

import pytest_asyncio

from api.middleware.database import setup_connection

@pytest_asyncio.fixture(scope="function")
async def delete_test_users():
    await _delete_test_users()
    yield
    await _delete_test_users()

async def _delete_test_users():
    try:
        conn = await setup_connection()

        await conn.execute("""
delete
from users
where lower(email) like '%@pytest.com'
""")

    except Exception as e:
        raise Exception(f"Error in fixture: {e}")
    finally:
        if conn: await conn.close()