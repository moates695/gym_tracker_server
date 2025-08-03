from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Literal
import re
import json
import smtplib
from email.mime.text import MIMEText
from email.message import EmailMessage
import os
import jwt
from datetime import datetime, timedelta, timezone
import bcrypt

from api.middleware.database import setup_connection
from api.middleware.token import *
from api.routes.auth import verify_token, verify_temp_token

router = APIRouter()

class Register(BaseModel):
    email: str = Field(pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    password: str = Field(min_length=8, max_length=36)
    username: str = Field(min_length=1, max_length=20)
    first_name: str = Field(min_length=1, max_length=255)
    last_name: str = Field(min_length=1, max_length=255)
    gender: Literal["male", "female", "other"]
    height: int = Field(ge=0, le=500)
    weight: int = Field(ge=0, le=500)
    goal_status: Literal["bulking", "cutting", "maintaining"]
    ped_status: Literal["natural", "juicing", "silent"]
    send_email: bool = True

    @field_validator('password')
    def password_complexity(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter.')
        if not re.search(r'[1-9]', v):
            raise ValueError('Password must contain at least one number.')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character.')
        return v

@router.post("/register")
async def register(req: Register):
    req_json = json.loads(req.model_dump_json())
    
    try:
        conn = await setup_connection()

        error_result = {
            "status": "error",
            "fields": []
        }

        for col in ["email", "username"]:
            exists = await conn.fetchval(
                f"""
                select exists (
                    select 1
                    from users
                    where lower({col}) = lower($1)
                )""", req_json[col]
            )
            if not exists: continue
            error_result["fields"].append(col)

        if error_result["fields"] != []:
            return error_result

        hashed_pwd = bcrypt.hashpw(req.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        row = await conn.fetchrow(
            """
            insert into users
            (email, password, username, first_name, last_name, gender)
            values
            ($1, $2, $3, $4, $5, $6)
            returning id
            """, req.email, hashed_pwd, req.username, req.first_name, req.last_name, req.gender
        )
        user_id = row["id"]

        data_to_tables = [
            {
                "key": 'height',
                "table": 'user_heights',
                "column": 'height',
            },
            {
                "key": 'weight',
                "table": 'user_weights',
                "column": 'weight',
            },
            {
                "key": 'goal_status',
                "table": 'user_goals',
                "column": 'goal_status',
            },
            {
                "key": 'ped_status',
                "table": 'user_ped_status',
                "column": 'ped_status',
            },
        ]

        for data_map in data_to_tables:
            await conn.execute(
                f"""
                insert into {data_map["table"]}
                (user_id, {data_map["column"]})
                values
                ($1, $2);
                """, user_id, req_json[data_map["key"]]
            )

        if req.send_email:
            await send_validation_email(req.email, user_id)

        return {
            "status": "success",
            "temp_token": generate_token(
                req.email,
                user_id,
                minutes=15,
                is_temp=True
            )
        }

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500)

    finally:
        if conn: await conn.close()

@router.post("/register/validate/resend")
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
    token = generate_token(email, user_id, minutes=15, is_temp=True)
    link = f"{os.getenv('SERVER_ADDRESS')}:{os.getenv('SERVER_PORT')}/register/validate/receive?token={token}"

    msg = EmailMessage()
    msg["Subject"] = "Gym Tracker Email Validation"
    msg["From"] = os.getenv("EMAIL")
    msg["To"] = email
    msg.set_content(f"Click this link to validate your email: {link}")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(os.getenv("EMAIL"), os.getenv("EMAIL_PWD"))
        smtp.send_message(msg)

@router.get("/register/validate/receive")
async def validate_user(token: str):
    try:
        conn = await setup_connection()

        decoded = decode_token(token, is_temp=True)
        
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

@router.get("/login")
async def login(credentials: dict = Depends(verify_token)):
    return await login_user(credentials)

@router.get("/register/validate/check")
async def validate_check(credentials: dict = Depends(verify_temp_token)):
    return await login_user(credentials)

async def login_user(credentials):
    try:
        account_state = await fetch_account_state(credentials["user_id"])
        auth_token = None
        if account_state == "good":
            auth_token = generate_token(
                credentials["email"],
                credentials["user_id"],
                days=30
            )

        return {
            "account_state": account_state,
            "auth_token": auth_token
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

@router.get("/register/check/username")
async def valid_username(username: str):
    try:
        conn = await setup_connection()

        exists = await conn.fetchval(
            """
            select exists (
                select 1
                from users
                where lower(username) = lower($1)
            )
            """,  username
        )

        return {
            "taken": exists
        }

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Uncaught exception")
    finally:
        if conn: await conn.close()

class SignIn(BaseModel):
    email: str = Field(pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    password: str = Field(min_length=8, max_length=36)

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
            "token": token
        }

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Uncaught exception")
    finally:
        if conn: await conn.close()