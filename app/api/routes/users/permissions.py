from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Annotated, Optional
import json

from app.api.routes.auth import verify_token
from app.api.middleware.database import setup_connection
from app.api.middleware.misc import *

router = APIRouter()

# all user accounts consent to username and workout data appearing in leaderboards 
# create account with private default, settings to switch to public

# username appears in friends search (searchable): public | private
# user workouts (workouts): public | friends | private
# user personal data (personal_data): public | friends | private