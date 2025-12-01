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
import base64
from email.message import EmailMessage
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import random

from app.api.middleware.database import setup_connection
from app.api.middleware.auth_token import *
from app.api.routes.auth import verify_token, verify_temp_token
from app.api.routes.users.get_data import fetch_user_data
from app.api.middleware.misc import *

router = APIRouter()

@router.get("/validate/resend")
async def resend_validation_email(send_email: bool = True, credentials: dict = Depends(verify_temp_token)):
    try:
        await send_validation_email(credentials["email"], credentials["user_id"], send_email)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500)
    return {}

async def send_validation_email(email: str, user_id: str, send_email: bool = True):
    code = str(random.randint(100000,999999))

    try:
        conn = await setup_connection()
        
        user_exists = await conn.fetchval(
            """
            select exists (
                select 1
                from users
                where id = $1
            )
            """, user_id
        )
        if not user_exists:
            raise HTTPException(status_code=400, detail="user does not exist")

        await conn.execute(
            """
            insert into user_codes
            (user_id, code)
            values
            ($1, $2)
            on conflict (user_id) do update
            set
                code = $2
            """, user_id, code
        )

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Uncaught exception")
    finally:
        if conn: await conn.close()

    if not send_email: return

    msg = EmailMessage()
    msg["To"] = email
    msg["Subject"] = "Gym Junkie Email Validation"
    msg["From"] = os.getenv("EMAIL")
    msg.set_content(f"Your validation code is:\n\n\t{code}\n\nNever share your code with anyone.")

    creds = Credentials(
        None,
        refresh_token=os.getenv("GOOGLE_REFRESH_TOKEN"),
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        token_uri="https://oauth2.googleapis.com/token"
    )

    service = build("gmail", "v1", credentials=creds)

    encoded_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    service.users().messages().send(
        userId="me",
        body={"raw": encoded_msg}
    ).execute()

@router.get("/validate/receive")
async def validate_user(code: str, credentials: dict = Depends(verify_temp_token)):
    try:
        conn = await setup_connection()

        is_verified = await conn.fetchval(
            """
            select is_verified
            from users
            where lower(email) = lower($1)
            """, credentials["email"]
        )

        if is_verified is None:
            return {
                "status": "error",
                "message": "user does not exist"
            }

        db_code = await conn.fetchval(
            """
            select code
            from user_codes
            where user_id = $1
            """, credentials["user_id"]
        )

        if db_code is None:
            return {
                "status": "error",
                "message": "code not set for user"
            }
        elif code != db_code:
            return {
                "status": "incorrect",
                "message": "code is not correct"
            }
        
        await conn.execute(
            """
            delete 
            from user_codes
            where user_id = $1
            """, credentials["user_id"]
        )

        if not is_verified:
            await conn.execute(
                """
                update users
                set is_verified = true
                where id = $1
                """, credentials["user_id"]
            )

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Uncaught exception")
    finally:
        if conn: await conn.close()

    return {
        "status": "verified",
        "auth_token": generate_token(
            credentials["email"],
            credentials["user_id"],
            days=30
        ),
        "user_data": await fetch_user_data(credentials["user_id"])
    }

# @router.get("/validate/check")
# async def validate_check(credentials: dict = Depends(verify_temp_token)):
#     return await login_user(credentials)