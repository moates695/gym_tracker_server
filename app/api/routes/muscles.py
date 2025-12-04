from fastapi import APIRouter, HTTPException, Security, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Literal
import jwt
import os
from datetime import datetime, timedelta, timezone
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import random

from app.api.middleware.database import setup_connection
from app.api.middleware.auth_token import *
from app.api.routes.auth import verify_token
from app.api.middleware.misc import SafeError

router = APIRouter()
security = HTTPBearer()

@router.get("/muscles/get_maps")
async def muscles_get_maps_route(credentials: dict = Depends(verify_token)):
    try:
        return await get_muscle_maps()
    except SafeError as e:
        raise e
    except Exception as e:
        print(str(e))
        raise Exception('uncaught error')

async def get_muscle_maps():
    try:
        conn = await setup_connection()

        rows = await conn.fetch(
            """
            select group_name, target_name
            from muscle_groups_targets
            """
        )

        group_to_targets = {}
        target_to_group = {}
        for row in rows:
            group_name = row["group_name"]
            target_name = row['target_name']
            
            if group_name not in group_to_targets.keys():
                group_to_targets[group_name] = []
            group_to_targets[group_name].append(target_name)

            target_to_group[target_name] = group_name

        return {
            "group_to_targets": group_to_targets,
            "target_to_group": target_to_group
        }

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Uncaught exception")
    finally:
        if conn: await conn.close()