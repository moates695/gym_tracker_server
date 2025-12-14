from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Annotated, Optional
import json

from app.api.routes.auth import verify_token
from app.api.middleware.database import setup_connection
from app.api.middleware.misc import *

router = APIRouter()

# all user accounts consent to username and workout data appearing in leaderboards 
# create account with private default, settings to switch to public

# username appears in friends search (searchable): public | private
# user workouts (workouts): public | friends | private
# user personal data: public | friends | private
#   name
#   gender
#   age
#   goal
#   height
#   weight

permission_keys = [
    "searchable",
    "workouts",
    "name",
    "gender",
    "age",
    "goal",
    "height",
    "weight",
]

def get_permission_values(key: str):
    if key == "searchable":
        return ["public", "private"]
    return ["public", "friends", "private"]

@router.get("/permissions/get")
async def users_friends_block(credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()

        rows = await conn.fetch(
            """
            select *
            from user_permissions
            where user_id = $1
            """, credentials["user_id"]
        )
        permissions = {
            row["permission_key"]: row["permission_value"]
            for row in rows
        }

        for key in permission_keys:
            if key not in permissions:
                permissions[key] = "private"
                await conn.execute(
                    """
                    insert into user_permissions
                    (user_id, permission_key, permission_value)
                    values
                    ($1, $2, 'private')
                    """, credentials["user_id"], key
                )
            elif permissions[key] not in get_permission_values(key):
                permissions[key] = "private"
                await conn.execute(
                    """
                    update user_permissions
                    set permission_value = 'private'
                    where user_id = $1
                    and permission_key = $2
                    """, credentials["user_id"], key
                )

        return {
            "permissions": permissions
        }

    except SafeError as e:
        raise e
    except Exception as e:
        print(str(e))
        raise Exception('uncaught error')
    finally:
        if conn: await conn.close()

class PermissionsUpdate(BaseModel):
    key: str
    value: str

@router.post("/permissions/update")
async def users_friends_block(req: PermissionsUpdate, credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()

        if req.value not in get_permission_values(req.key):
            raise SafeError(f"value '{req.value}' not allowed for key '{req.key}'")
        
        await conn.execute(
            """
            update user_permissions
            set permission_value = $1
            where user_id = $2
            and permission_key = $3
            """,
            req.value,
            credentials["user_id"],
            req.key
        )

        return {
            "status": "success"
        }

    except SafeError as e:
        raise e
    except Exception as e:
        print(str(e))
        raise Exception('uncaught error')
    finally:
        if conn: await conn.close()

