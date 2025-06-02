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
                    "bicep": 100,
                    "forearm": 20
                },
                "is_body_weight": False
            },
            {
                "id": "001",
                "name": "Push-Up",
                "targets": {
                    "chest": 80,
                    "tricep": 60,
                    "shoulder": 40
                },
                "is_body_weight": True
            },
            {
                "id": "002",
                "name": "Pull-Up",
                "targets": {
                    "lats": 100,
                    "bicep": 60,
                    "forearm": 30
                },
                "is_body_weight": True
            },
            {
                "id": "003",
                "name": "Barbell Squat",
                "targets": {
                    "quadriceps": 100,
                    "glutes": 80,
                    "hamstring": 60
                },
                "is_body_weight": False
            },
            {
                "id": "004",
                "name": "Deadlift",
                "targets": {
                    "glutes": 90,
                    "hamstring": 70,
                    "lower_back": 80
                },
                "is_body_weight": False
            },
            {
                "id": "005",
                "name": "Plank",
                "targets": {
                    "core": 100,
                    "shoulder": 20,
                    "lower_back": 30
                },
                "is_body_weight": True
            },
            {
                "id": "006",
                "name": "Overhead Shoulder Press",
                "targets": {
                    "shoulder": 100,
                    "tricep": 50
                },
                "is_body_weight": False
            },
            {
                "id": "007",
                "name": "Dumbbell Lateral Raise",
                "targets": {
                    "shoulder": 100,
                    "trapezius": 40
                },
                "is_body_weight": False
            },
            {
                "id": "008",
                "name": "Leg Press",
                "targets": {
                    "quadriceps": 100,
                    "glutes": 70,
                    "hamstring": 50
                },
                "is_body_weight": False
            },
            {
                "id": "009",
                "name": "Tricep Dip",
                "targets": {
                    "tricep": 100,
                    "chest": 40,
                    "shoulder": 30
                },
                "is_body_weight": True
            },
            {
                "id": "010",
                "name": "Russian Twist",
                "targets": {
                    "oblique": 100,
                    "core": 60
                },
                "is_body_weight": True
            },
            {
                "id": "011",
                "name": "Lunge",
                "targets": {
                    "quadriceps": 90,
                    "glutes": 70,
                    "hamstring": 60
                },
                "is_body_weight": True
            },
            {
                "id": "012",
                "name": "Bench Press",
                "targets": {
                    "chest": 100,
                    "tricep": 60,
                    "shoulder": 60
                },
                "is_body_weight": False
            },
            {
                "id": "013",
                "name": "Mountain Climber",
                "targets": {
                    "core": 80,
                    "shoulder": 40,
                    "quadriceps": 50
                },
                "is_body_weight": True
            },
            {
                "id": "014",
                "name": "Bent-Over Row",
                "targets": {
                    "lats": 90,
                    "trapezius": 60,
                    "bicep": 40
                },
                "is_body_weight": False
            },
            {
                "id": "015",
                "name": "Glute Bridge",
                "targets": {
                    "glutes": 100,
                    "hamstring": 40,
                    "core": 30
                },
                "is_body_weight": True
            },
            {
                "id": "016",
                "name": "Burpee",
                "targets": {
                    "core": 60,
                    "quadriceps": 50,
                    "chest": 50,
                    "shoulder": 30
                },
                "is_body_weight": True
            },
            {
                "id": "017",
                "name": "Seated Calf Raise",
                "targets": {
                    "calves": 100
                },
                "is_body_weight": False
            },
            {
                "id": "018",
                "name": "Hanging Leg Raise",
                "targets": {
                    "core": 100,
                    "hip_flexors": 40
                },
                "is_body_weight": True
            },
            {
                "id": "019",
                "name": "Face Pull",
                "targets": {
                    "rear_deltoid": 90,
                    "trapezius": 60
                },
                "is_body_weight": False
            },
            {
                "id": "020",
                "name": "Farmer's Carry",
                "targets": {
                    "forearm": 80,
                    "trapezius": 60,
                    "core": 40
                },
                "is_body_weight": False
            }
        ]
    }

@router.get("/exercise/history")
async def protected_route(id: str, credentials: dict = Depends(verify_token)):
    now = datetime.now(timezone.utc).timestamp()
    return {
        "n_rep_max": {
            "all_time": {
                "1": { "weight": 155.8, "timestamp": now - 1000 * 60 * 60 * 24 * 30 },
                "3": { "weight": 152.9, "timestamp": now - 1000 * 60 * 60 * 24 * 180 },
                "5": { "weight": 143.2, "timestamp": now - 1000 * 60 * 60 * 24 * 90 },
                "10": { "weight": 135.6, "timestamp": now - 1000 * 60 * 60 * 24 * 14 },
                "11": { "weight": 133.5, "timestamp": now - 1000 * 60 * 60 * 24 * 7 },
                "20": { "weight": 90.9, "timestamp": now - 1000 * 60 * 60 * 24 * 400 }
            },
            "history": {
                "1": [
                    { "weight": 148.6, "timestamp": now - 1000 * 60 * 60 * 24 * 1 },
                    { "weight": 149.0, "timestamp": now - 1000 * 60 * 60 * 24 * 3 },
                    { "weight": 148.6, "timestamp": now - 1000 * 60 * 60 * 24 * 5 },
                    { "weight": 152.2, "timestamp": now - 1000 * 60 * 60 * 24 * 10 },
                    { "weight": 151.0, "timestamp": now - 1000 * 60 * 60 * 24 * 20 },
                    { "weight": 155.8, "timestamp": now - 1000 * 60 * 60 * 24 * 30 },
                    { "weight": 150.8, "timestamp": now - 1000 * 60 * 60 * 24 * 60 },
                    { "weight": 150.5, "timestamp": now - 1000 * 60 * 60 * 24 * 80 },
                    { "weight": 153.7, "timestamp": now - 1000 * 60 * 60 * 24 * 150 },
                    { "weight": 153.7, "timestamp": now - 1000 * 60 * 60 * 24 * 300 },
                    { "weight": 148.1, "timestamp": now - 1000 * 60 * 60 * 24 * 370 }
                ],
                "3": [
                    { "weight": 141.0, "timestamp": now - 1000 * 60 * 60 * 24 * 2 },
                    { "weight": 148.5, "timestamp": now - 1000 * 60 * 60 * 24 * 10 },
                    { "weight": 146.2, "timestamp": now - 1000 * 60 * 60 * 24 * 20 },
                    { "weight": 142.9, "timestamp": now - 1000 * 60 * 60 * 24 * 40 },
                    { "weight": 145.1, "timestamp": now - 1000 * 60 * 60 * 24 * 60 },
                    { "weight": 143.9, "timestamp": now - 1000 * 60 * 60 * 24 * 90 },
                    { "weight": 149.9, "timestamp": now - 1000 * 60 * 60 * 24 * 180 },
                    { "weight": 149.4, "timestamp": now - 1000 * 60 * 60 * 24 * 250 },
                    { "weight": 144.7, "timestamp": now - 1000 * 60 * 60 * 24 * 300 }
                ],
                "5": [
                    { "weight": 138.2, "timestamp": now - 1000 * 60 * 60 * 24 * 1 },
                    { "weight": 137.0, "timestamp": now - 1000 * 60 * 60 * 24 * 3 },
                    { "weight": 140.2, "timestamp": now - 1000 * 60 * 60 * 24 * 5 },
                    { "weight": 139.9, "timestamp": now - 1000 * 60 * 60 * 24 * 10 },
                    { "weight": 141.5, "timestamp": now - 1000 * 60 * 60 * 24 * 40 },
                    { "weight": 143.2, "timestamp": now - 1000 * 60 * 60 * 24 * 75 },
                    { "weight": 139.7, "timestamp": now - 1000 * 60 * 60 * 24 * 90 },
                    { "weight": 142.6, "timestamp": now - 1000 * 60 * 60 * 24 * 180 },
                    { "weight": 140.8, "timestamp": now - 1000 * 60 * 60 * 24 * 365 }
                ],
                "10": [
                    { "weight": 128.1, "timestamp": now - 1000 * 60 * 60 * 24 * 1 },
                    { "weight": 121.5, "timestamp": now - 1000 * 60 * 60 * 24 * 7 },
                    { "weight": 128.4, "timestamp": now - 1000 * 60 * 60 * 24 * 14 },
                    { "weight": 130.0, "timestamp": now - 1000 * 60 * 60 * 24 * 20 },
                    { "weight": 126.7, "timestamp": now - 1000 * 60 * 60 * 24 * 30 },
                    { "weight": 129.6, "timestamp": now - 1000 * 60 * 60 * 24 * 50 },
                    { "weight": 129.1, "timestamp": now - 1000 * 60 * 60 * 24 * 90 },
                    { "weight": 122.6, "timestamp": now - 1000 * 60 * 60 * 24 * 180 },
                    { "weight": 125.8, "timestamp": now - 1000 * 60 * 60 * 24 * 365 }
                ],
                "11": [
                    { "weight": 118.9, "timestamp": now - 1000 * 60 * 60 * 24 * 3 },
                    { "weight": 126.5, "timestamp": now - 1000 * 60 * 60 * 24 * 7 },
                    { "weight": 120.4, "timestamp": now - 1000 * 60 * 60 * 24 * 15 },
                    { "weight": 124.1, "timestamp": now - 1000 * 60 * 60 * 24 * 30 },
                    { "weight": 118.6, "timestamp": now - 1000 * 60 * 60 * 24 * 45 },
                    { "weight": 117.6, "timestamp": now - 1000 * 60 * 60 * 24 * 90 },
                    { "weight": 123.7, "timestamp": now - 1000 * 60 * 60 * 24 * 180 },
                    { "weight": 119.7, "timestamp": now - 1000 * 60 * 60 * 24 * 270 },
                    { "weight": 122.9, "timestamp": now - 1000 * 60 * 60 * 24 * 400 }
                ],
                "20": [
                    { "weight": 91.8, "timestamp": now - 1000 * 60 * 60 * 24 * 14 },
                    { "weight": 94.4, "timestamp": now - 1000 * 60 * 60 * 24 * 45 },
                    { "weight": 93.7, "timestamp": now - 1000 * 60 * 60 * 24 * 60 },
                    { "weight": 92.3, "timestamp": now - 1000 * 60 * 60 * 24 * 90 },
                    { "weight": 96.7, "timestamp": now - 1000 * 60 * 60 * 24 * 120 },
                    { "weight": 97.9, "timestamp": now - 1000 * 60 * 60 * 24 * 150 },
                    { "weight": 95.3, "timestamp": now - 1000 * 60 * 60 * 24 * 250 },
                    { "weight": 99.9, "timestamp": now - 1000 * 60 * 60 * 24 * 400 },
                    { "weight": 95.8, "timestamp": now - 1000 * 60 * 60 * 24 * 420 }
                ]
            }
        }
    }