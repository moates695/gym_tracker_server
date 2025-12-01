from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
import re
import json
import smtplib
from email.message import EmailMessage
import os
from datetime import date
import bcrypt
import traceback

from app.api.middleware.database import setup_connection
from app.api.middleware.auth_token import *
from app.api.routes.auth import verify_token, verify_temp_token
from app.api.routes.register.validate import send_validation_email
from app.api.routes.users.get_data import fetch_user_data
from app.api.middleware.misc import *

router = APIRouter()

@router.get("/login")
async def login(send_email: bool = True, credentials: dict = Depends(verify_token)):
    return await login_user(send_email, credentials)

async def login_user(send_email, credentials):
    try:
        account_state = await fetch_account_state(credentials["user_id"])
        token = None
        user_data = None
        if account_state == "good":
            token = generate_token(
                credentials["email"],
                credentials["user_id"],
                days=30
            )
            user_data = await fetch_user_data(credentials["user_id"])
        elif account_state == "unverified":
            await send_validation_email(credentials["email"], credentials["user_id"], send_email)
            token = generate_token(
                credentials["email"],
                credentials["user_id"],
                minutes=30,
                is_temp=True
            )

        return {
            "account_state": account_state,
            "token": token,
            "user_data": user_data 
        }

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Uncaught exception")

async def fetch_account_state(user_id):
    try:
        conn = await setup_connection()

        is_verified = await conn.fetchval(
            """
            select is_verified
            from users
            where id = $1
            """, user_id
        )

        if is_verified is None:
            return "none"
        elif not is_verified:
            return "unverified" 
        else:
            return "good"
        
    except Exception as e:
        raise e
    finally:
        if conn: await conn.close()