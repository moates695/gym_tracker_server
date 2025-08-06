from fastapi import APIRouter, HTTPException, Security, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from api.middleware.database import setup_connection
import jwt
import os
from datetime import datetime, timedelta, timezone
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import random

from api.middleware.token import *
from api.routes.auth import verify_token

router = APIRouter()
security = HTTPBearer()

@router.get("/muscles/get_maps")
async def workout_save(credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()

        rows = await conn.fetch(
            """
            select mg.name as group_name, mt.name as target_name
            from muscle_groups mg
            inner join muscle_targets mt
            on mt.muscle_group_id = mg.id
            """
        ) # todo: use new view instead

        group_to_targets = {}
        target_to_group = {}
        for row in rows:
            group_name = row["group_name"]
            target_name = row['target_name']
            
            if group_name not in group_to_targets.keys():
                group_to_targets[group_name] = []
            group_to_targets[group_name].append(target_name)

            target_to_group[target_name] = group_name

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Uncaught exception")
    finally:
        if conn: await conn.close()

    return {
        "group_to_targets": group_to_targets,
        "target_to_group": target_to_group
    }