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
from app.api.routes.register.login import login_user
from app.api.routes.users.get_data import fetch_user_data
from app.api.middleware.misc import *

router = APIRouter()

# todo dont use temp token here, use user login details instead (user_id then lookup email?)
@router.post("/validate/resend")
async def resend_validation_email(credentials: dict = Depends(verify_temp_token)):
    try:
        await send_validation_email(credentials["email"], credentials["user_id"])
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500)
    return {}

async def send_validation_email(email: str, user_id: str):
    token = generate_token(email, user_id, minutes=15)
    link = f"{os.getenv('SERVER_ADDRESS')}/register/validate/receive?token={token}"

    msg = EmailMessage()
    msg["Subject"] = "Gym Tracker Email Validation"
    msg["From"] = os.getenv("EMAIL")
    msg["To"] = email
    msg.set_content(f"Click this link to validate your email: {link}")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(os.getenv("EMAIL"), os.getenv("EMAIL_PWD"))
        smtp.send_message(msg)

@router.get("/validate/receive")
async def validate_user(token: str):
    try:
        conn = await setup_connection()

        try:
            decoded = decode_token(token)
        except Exception as e:
            raise HTTPException(status_code=401)
        
        is_valid = await conn.fetchval(
            """
            select exists (
                select 1
                from users
                where lower(email) = lower($1)
                and is_verified = false
            )
            """, decoded["email"]
        )

        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Email '{decoded['email']}' does not exist or is already verified")

        await conn.execute(
            """
            update users
            set is_verified = true
            where lower(email) = lower($1)
            """, decoded["email"]
        )

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Uncaught exception")
    finally:
        if conn: await conn.close()

    return {
        "message": "email validation successful"
    }

@router.get("/validate/check")
async def validate_check(credentials: dict = Depends(verify_temp_token)):
    return await login_user(credentials)