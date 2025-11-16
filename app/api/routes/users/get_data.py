from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Annotated, Optional
import json

from app.api.routes.auth import verify_token
from app.api.middleware.database import setup_connection
from app.api.middleware.misc import *

router = APIRouter()

@router.get("/users/data/get")
async def users_data(credentials: dict = Depends(verify_token)):
    try:
        return {
            "user_data": await fetch_user_data(credentials["user_id"])
        }
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        return HTTPException(status_code=500)

async def fetch_user_data(user_id: str) -> dict | None:
    try:
        conn = await setup_connection()

        row = await conn.fetchrow(
            """
            select distinct on (u.id) u.*, w.weight, h.height, p.ped_status, g.goal_status
            from users u
            inner join user_weights w
            on w.user_id = u.id
            inner join user_heights h
            on h.user_id = u.id
            inner join user_ped_status p
            on p.user_id = u.id
            inner join user_goals g
            on g.user_id = u.id
            where u.id = $1
            order by u.id, w.created_at desc, h.created_at desc, p.created_at desc, g.created_at desc
            """, user_id
        )

        if row is None: raise Exception("user data not found")

        return {
            "user_id": row["id"],
            "email": row["email"],
            "username": row["username"],
            "first_name": row["first_name"],
            "last_name": row["last_name"],
            "gender": row["gender"],
            "goal_status": row["goal_status"],
            "height": row["height"],
            "ped_status": row["ped_status"],
            "weight": row["weight"],
        }

    except Exception as e:
        raise e
    finally:
        if conn: await conn.close()