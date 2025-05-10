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
from api.routes.auth import verify_token

router = APIRouter()
security = HTTPBearer()

# return exercises + user stats for previous set timespan

@router.get("/exercises/list/all")
async def protected_route(credentials: dict = Depends(verify_token)):
    return {
        "exercises": [
            {
                "id": "000",
                "name": "Dumbbell Bicep Curl",
                "targets": {
                    "bicep": "100",
                    "forearm": "20"
                },
                "is_body_weight": False
            },
            {
                "id": "001",
                "name": "Push-Up",
                "targets": {
                    "chest": "80",
                    "tricep": "60",
                    "shoulder": "40"
                },
                "is_body_weight": True
            },
            {
                "id": "002",
                "name": "Pull-Up",
                "targets": {
                    "lats": "100",
                    "bicep": "60",
                    "forearm": "30"
                },
                "is_body_weight": True
            },
            {
                "id": "003",
                "name": "Barbell Squat",
                "targets": {
                    "quadriceps": "100",
                    "glutes": "80",
                    "hamstring": "60"
                },
                "is_body_weight": False
            },
            {
                "id": "004",
                "name": "Deadlift",
                "targets": {
                    "glutes": "90",
                    "hamstring": "70",
                    "lower_back": "80"
                },
                "is_body_weight": False
            },
            {
                "id": "005",
                "name": "Plank",
                "targets": {
                    "core": "100",
                    "shoulder": "20",
                    "lower_back": "30"
                },
                "is_body_weight": True
            },
            {
                "id": "006",
                "name": "Overhead Shoulder Press",
                "targets": {
                    "shoulder": "100",
                    "tricep": "50"
                },
                "is_body_weight": False
            },
            {
                "id": "007",
                "name": "Dumbbell Lateral Raise",
                "targets": {
                    "shoulder": "100",
                    "trapezius": "40"
                },
                "is_body_weight": False
            },
            {
                "id": "008",
                "name": "Leg Press",
                "targets": {
                    "quadriceps": "100",
                    "glutes": "70",
                    "hamstring": "50"
                },
                "is_body_weight": False
            },
            {
                "id": "009",
                "name": "Tricep Dip",
                "targets": {
                    "tricep": "100",
                    "chest": "40",
                    "shoulder": "30"
                },
                "is_body_weight": True
            },
            {
                "id": "010",
                "name": "Russian Twist",
                "targets": {
                    "oblique": "100",
                    "core": "60"
                },
                "is_body_weight": True
            }
        ]
    }