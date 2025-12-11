from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Annotated, Optional
import json

from app.api.routes.auth import verify_token
from app.api.middleware.database import setup_connection
from app.api.middleware.misc import *

router = APIRouter()

# user friend workflow
# search for username (those that arent blocked)
# click add to request friend (if request not open)
# other user accepts, denies, blocks request
# blocking user unfriends if friends before

# from homepage, click through to friends page to, 
#   add new friends
#   remove friends
#   look at friends stats?

@router.get("/users/search")
async def users_search(credentials: dict = Depends(verify_token)):
    return {}