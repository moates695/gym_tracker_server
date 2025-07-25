from fastapi import APIRouter, HTTPException, Security, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from api.middleware.database import setup_connection
import jwt
import os
from datetime import datetime, timedelta, timezone
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from functools import partial

from api.middleware.token import *

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
        if decoded is None:
            raise Exception("Token is invalid")
        elif is_token_expired(decoded):
            raise Exception("Token expired")
        return decoded
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

async def verify_temp_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    return await verify_token(credentials, is_temp=True)
