from fastapi import APIRouter

from app.api.routes.stats import distributions
from app.api.routes.stats import favourites
from app.api.routes.stats import history
from app.api.routes.stats import leaderboard
from app.api.routes.stats import workout_totals

router = APIRouter(prefix="/stats")

router.include_router(distributions.router)
router.include_router(favourites.router)
router.include_router(history.router)
router.include_router(leaderboard.router)
router.include_router(workout_totals.router)