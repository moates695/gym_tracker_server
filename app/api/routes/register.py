from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import Literal
import re
import psycopg2 as pg
import json
import smtplib
from email.message import EmailMessage
import os
import jwt
from datetime import datetime, timedelta, timezone

from api.middleware.database import setup_connection

router = APIRouter()

class Register(BaseModel):
    email: str = Field(pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    password: str = Field(min_length=8, max_length=36)
    username: str = Field(min_length=1, max_length=20)
    first_name: str = Field(min_length=1, max_length=255)
    last_name: str = Field(min_length=1, max_length=255)
    gender: Literal["male", "female", "other"]
    height: int = Field(ge=20, le=300)
    weight: int = Field(ge=20, le=300)
    goal_status: Literal["bulking", "cutting", "maintaining"]
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
        conn, cur = setup_connection()

        for field in ["email", "username"]:
            cur.execute("""
    select exists (
        select 1
        from users
        where lower(%s) = lower(%s)
    )""", (field, req_json[field]))
        
            if cur.fetchone()[0]:
                raise HTTPException(status_code=400, detail=f"{field} already exists")

        cur.execute("""
insert into users
(email, password, username, first_name, last_name, gender, height, weight, goal_status)
values
(%s, %s, %s, %s, %s, %s, %s, %s, %s)""", 
        (req.email, req.password, req.username, req.first_name, req.last_name, req.gender, req.height, req.weight, req.goal_status))
        conn.commit()

        if req.send_email:
            await send_validation_email(req.email)

    except HTTPException as e:
        raise e
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail="Uncaught exception")
    
    finally:
        if cur: cur.close()
        if conn: conn.close()

    return {}

class Validate(BaseModel):
    email: str = Field(pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

@router.post("/register/send_validation")
async def _send_validation_email(req: Validate):
    try:
        await send_validation_email(req.email)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error sending validation email")

async def send_validation_email(email):
    payload = {
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15)
    }
    token = jwt.encode(payload, os.getenv("SECRET_KEY"), algorithm="HS256")
    link = f"{os.getenv('SERVER_ADDRESS')}:{os.getenv('SERVER_PORT')}/register/validate_user?token={token}"

    msg = EmailMessage()
    msg["Subject"] = "Gym Tracker Email Validation"
    msg["From"] = os.getenv("EMAIL")
    msg["To"] = email
    msg.set_content(f"Click this <a href={link}>link</a> to validate your email.")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(os.getenv("EMAIL"), os.getenv("EMAIL_PWD"))
        smtp.send_message(msg)


@router.post("/register/validate_user")
async def validate_user():
    pass