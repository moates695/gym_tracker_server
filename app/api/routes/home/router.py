from fastapi import APIRouter

from app.api.routes.home import home

router = APIRouter(prefix="/home")

router.include_router(home.router)