from fastapi import APIRouter

from app.api.routes.users import data_history
from app.api.routes.users import get_data
from app.api.routes.users import update_data


router = APIRouter(prefix="/users")

router.include_router(data_history.router)
router.include_router(get_data.router)
router.include_router(update_data.router)