from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Annotated, Optional
import json

from app.api.routes.auth import verify_token
from app.api.middleware.database import setup_connection
from app.api.middleware.misc import *

router = APIRouter()

@router.get("/users/data/get/history")
async def users_data_get_history(credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()

        history = {}
        for key, data_map in user_data_tables_map.items():
            if data_map["table"] == "users": continue

            rows = await conn.fetch(
                f"""
                select *
                from {data_map["table"]}
                where user_id = $1
                order by created_at desc
                """, credentials["user_id"]
            )

            history[key] = [{
                "value": row[data_map["column"]],
                "created_at": row["created_at"].timestamp()
            } for row in rows]

        return {
            "data_history": history
        }

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500)
    finally:
        if conn: await conn.close()