from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Literal

router = APIRouter()

class Authenticate(BaseModel):
    token: str

@router.post("/authenticate")
async def authenticate(req: Authenticate):
    return {}

