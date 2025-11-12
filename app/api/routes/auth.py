from fastapi import APIRouter, HTTPException, Security, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Literal
import jwt
import os
from datetime import datetime, timedelta, timezone
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from functools import partial
import asyncio

from app.api.middleware.database import setup_connection
from app.api.middleware.auth_token import *

router = APIRouter()
security = HTTPBearer()

class TokenPayload(BaseModel):
    email: str
    exp: int
    iat: int

async def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security), 
    is_temp: bool = False
) -> dict:
    try:
        decoded = decode_token(credentials.credentials, is_temp=is_temp)
        if is_token_expired(decoded):
            raise Exception("Token expired")
        return decoded
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

async def verify_temp_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    return await verify_token(credentials, is_temp=True)

@router.get("/protected")
async def workout_save(credentials: dict = Depends(verify_token)):
    return {}

@router.get("/protected_temp")
async def workout_save(credentials: dict = Depends(verify_temp_token)):
    return {}