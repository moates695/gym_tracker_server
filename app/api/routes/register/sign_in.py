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
from app.api.routes.users.get_data import fetch_user_data
from app.api.middleware.misc import *

router = APIRouter()

class SignIn(BaseModel):
    email: str = email_field
    password: str = password_field

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

        token = None
        user_data = None
        if row is None:
            status = "none"
        elif bcrypt.checkpw(req.password.encode('utf-8'), row['password'].encode('utf-8')):
            if row["is_verified"]:
                status = "signed-in"
                token = generate_token(
                    req.email,
                    row["id"],
                    days=30
                )
                user_data = await fetch_user_data(row["id"])
            else:
                status = "unverified"
                token = generate_token(
                    req.email,
                    row["id"],
                    minutes=15,
                    is_temp=True
                )
        else:
            status = "incorrect-password"

        return {
            "status": status,
            "token": token,
            "user_data": user_data
        }

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Uncaught exception")
    finally:
        if conn: await conn.close()