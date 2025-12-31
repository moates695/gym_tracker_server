from fastapi import APIRouter

from app.api.routes.home import muscles_history
from app.api.routes.home import volume_frequency
from app.api.routes.home import online_friends

router = APIRouter(prefix="/home")

router.include_router(muscles_history.router)
router.include_router(volume_frequency.router)
router.include_router(online_friends.router)