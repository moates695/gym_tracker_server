from fastapi import APIRouter

from app.api.routes.workout import overview_stats
from app.api.routes.workout import save

router = APIRouter(prefix="/workout")

router.include_router(overview_stats.router)
router.include_router(save.router)