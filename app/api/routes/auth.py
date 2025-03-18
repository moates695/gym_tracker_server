from fastapi import APIRouter, HTTPException, Security, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from api.middleware.database import setup_connection
import jwt
import os
from datetime import datetime, timedelta, timezone
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from api.middleware.token import *

router = APIRouter()
security = HTTPBearer()

class TokenPayload(BaseModel):
    email: str
    exp: int
    iat: int

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    try:
        token = credentials.credentials
        payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=["HS256"])
        return payload
    
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

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


