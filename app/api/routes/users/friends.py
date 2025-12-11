from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Annotated, Optional
import json

from app.api.routes.auth import verify_token
from app.api.middleware.database import setup_connection
from app.api.middleware.misc import *

router = APIRouter()

# user friend workflow
# search for username (those that arent blocked)
# click add to request friend (if request not open)
# other user accepts, denies, blocks request
# blocking user unfriends if friends before

# from homepage, click through to friends page to, 
#   add new friends
#   remove friends
#   look at friends stats?

@router.get("/search")
async def users_search(username: str, credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()

        rows = await conn.fetch(
            """
            select
                u.*,
                (f.user1_id is not null or f.user2_id is not null) as is_friend
            from users u
            left join friends f
                on (f.user1_id = u.id and f.user2_id = $1)
                or (f.user2_id = u.id and f.user1_id = $1)
            where id != $1
            and username ilike $2 || '%'
            and id not in (
                select blocked_id
                from blocked_users
                where victim_id = $1
            )
            order by username
            limit 50
            """,
            credentials["user_id"],
            username.strip()
        )

        return {
            "matches": [{
                "id": row["id"],
                "username": row["username"],
                "is_friend": row["is_friend"]
            } for row in rows]
        }

    except SafeError as e:
        raise e
    except Exception as e:
        print(str(e))
        raise Exception('uncaught error')
    finally:
        if conn: await conn.close()