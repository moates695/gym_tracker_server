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
    return await verify_token(credentials, is_temp=False)

@router.get("/protected")
async def protected_route(credentials: dict = Depends(verify_token)):
    return {}

# class Authenticate(BaseModel):
#     token: str

# @router.post("/authenticate")
# async def authenticate(req: Authenticate):
#     try:
#         conn = await setup_connection()

#         decoded = decode_token(req.token)
#         if is_token_expired(decoded):
#             return JSONResponse(content={"status": "expired"})

#         is_validated = await conn.fetchval(
#             """
#             select is_validated
#             from users
#             where lower(email) = $1
#             """, decoded["email"]
#         )
        
#         if is_validated == None:
#             return JSONResponse(content={"status": "not-registered"})
#         elif not is_validated:
#             return JSONResponse(content={"status": "not-validated"})
#         else:
#             return JSONResponse(
#                 content={
#                     "status": "good",
#                     "token": generate_token(decoded["email"], days=30)
#                 }
#             )

#     except HTTPException as e:
#         return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
#     except Exception as e:
#         print(e)
#         raise HTTPException(status_code=500)

#     finally:
#         if conn: await conn.close()


