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

@router.get("/check/username")
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

    except SafeError as e:
        raise e
    except Exception as e:
        print(str(e))
        raise Exception('uncaught error')
    finally:
        if conn: await conn.close()


@router.get("/check/email")
async def valid_username(email: str):
    try:
        conn = await setup_connection()

        exists = await conn.fetchval(
            """
            select exists (
                select 1
                from users
                where lower(email) = lower($1)
            )
            """, email
        )

        return {
            "taken": exists
        }

    except SafeError as e:
        raise e
    except Exception as e:
        print(str(e))
        raise Exception('uncaught error')
    finally:
        if conn: await conn.close()