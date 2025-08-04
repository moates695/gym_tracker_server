from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Annotated, Literal, Optional
import re
import json
import smtplib
from email.mime.text import MIMEText
from email.message import EmailMessage
import os
import jwt
from datetime import datetime, timedelta, timezone
import bcrypt

from api.routes.auth import verify_token
from api.middleware.database import setup_connection
from api.middleware.misc import *

router = APIRouter()

@router.get("/users/data/get")
async def users_data(credentials: dict = Depends(verify_token)):
    try:
        user_data = await fetch_user_data(credentials["user_id"])
        return {
            "user_data": user_data
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
            select *
            from user_data
            where id = $1
            """, user_id
        )

        if row is None: raise Exception("user data not found")

        return {
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

class Update(BaseModel):
    first_name: Optional[Annotated[str, name_field]] = None
    last_name: Optional[Annotated[str, name_field]] = None
    gender: Optional[gender_literal] = None
    height: Optional[Annotated[float, height_field]] = None
    weight: Optional[Annotated[float, weight_field]] = None
    goal_status: Optional[goal_status_literal] = None
    ped_status: Optional[ped_status_literal] = None

@router.put("/users/data/update")
async def users_weight(req: Update, credentials: dict = Depends(verify_token)):
    req_json = json.loads(req.model_dump_json())

    try:
        conn = await setup_connection()

        for key, value in req_json.items():
            if value is None: continue
            data_map = get_user_data_map(key)
            if data_map["table"] == "users":
                await conn.execute(
                    f"""
                    update users
                    set {data_map["column"]} = $2
                    where id = $1
                    """, credentials["user_id"], value
                )
            else:
                await conn.execute(
                    f"""
                    insert into {data_map["table"]}
                    (user_id, {data_map["column"]})
                    values
                    ($1, $2);
                    """, credentials["user_id"], value
                )

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500)
    finally:
        if conn: await conn.close()

@router.get("/users/data/get/history")
async def users_data_get_history(credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()

        history = {}
        for data_map in user_data_to_tables:
            if data_map["table"] == "users": continue

            rows = await conn.fetch(
                f"""
                select {data_map["column"]}, created_at
                from {data_map["table"]}
                where user_id = $1
                order by created_at desc
                """, credentials["user_id"]
            )

            temp = []
            for row in rows:
                temp.append({
                    "value": row[data_map["column"]],
                    "created_at": row["created_at"].timestamp()
                })

            history[data_map["key"]] = temp

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