from fastapi import APIRouter

from app.api.routes.exercises import list_all
from app.api.routes.exercises import history

router = APIRouter(prefix="/exercises")

router.include_router(list_all.router)
router.include_router(history.router)