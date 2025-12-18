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

class SignIn(BaseModel):
    email: str = email_field
    password: str = password_field
    send_email: bool = True

@router.post("/sign-in")
async def sign_in(req: SignIn):
    try:
        conn = await setup_connection()

        row = await conn.fetchrow(
            """
            select id, password, is_verified
            from users
            where lower(email) = lower($1)
            """,  req.email
        )

        temp_token = None
        if row is None:
            status = "none"
        elif bcrypt.checkpw(req.password.encode('utf-8'), row['password'].encode('utf-8')):
            if req.email.strip().lower() == "app@review.com":
                return await sign_in_reviewer(req.email, row["id"])
            status = "good"
            temp_token = generate_token(
                req.email,
                row["id"],
                minutes=15,
                is_temp=True
            )
            await send_validation_email(req.email, row["id"], send_email=req.send_email)   
        else:
            status = "incorrect-password"

        return {
            "status": status,
            "temp_token": temp_token,
        }

    except SafeError as e:
        raise e
    except Exception as e:
        print(str(e))
        raise Exception('uncaught error')
    finally:
        if conn: await conn.close()

async def sign_in_reviewer(email: str, user_id: str):
    return {
        "status": "reviewer",
        "auth_token": generate_token(
            email,
            user_id,
            days=30,
        ),
        "user_data": await fetch_user_data(user_id)
    }