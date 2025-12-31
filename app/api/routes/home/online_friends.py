from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from datetime import datetime, timezone, timedelta
from fastapi.security import HTTPBearer
from copy import deepcopy
import math

from app.api.middleware.database import setup_connection
from app.api.middleware.auth_token import *
from app.api.routes.auth import verify_token
from app.api.middleware.misc import *
from app.api.routes.exercises.list_all import get_days_past
from app.api.routes.muscles import get_muscle_maps

router = APIRouter()
security = HTTPBearer()

@router.get("/online-friends")
async def online_friends(credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()
        
        has_friends = await conn.fetchval(
            """
            select exists (
                select 1
                from friends
                where user1_id = $1
                or user2_id = $1
            )
            """, credentials["user_id"]
        )
        if not has_friends:
            return {
                "data": {
                    "has_friends": False,
                    "online_friends": []
                }
            }

        return_count = 8

        rows = await conn.fetch(
            """
            select u.username
            from online_users of
            inner join users u
            on of.user_id = u.id
            where of.is_online = true
            and user_id in (
                select user1_id
                from friends
                where user2_id = $1
                union
                select user2_id
                from friends
                where user1_id = $1
            )
            limit $2
            """, credentials["user_id"], return_count
        )

        num_friends = await conn.fetchval(
            """
            select count(*)
            from online_users of
            where of.is_online = true
            and user_id in (
                select user1_id
                from friends
                where user2_id = $1
                union
                select user2_id
                from friends
                where user1_id = $1
            )
            """, credentials["user_id"]
        )
        
        online_friends = []
        for row in rows:
            online_friends.append(str(row["username"]))

        return {
            "data": {
                "has_friends": True,
                "online_friends": online_friends,
                "more_online_friends": num_friends > return_count
            }
        }

    except SafeError as e:
        raise e
    except Exception as e:
        print(str(e))
        raise Exception('uncaught error')
    finally:
        if conn: await conn.close()