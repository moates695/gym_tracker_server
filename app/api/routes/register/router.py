from fastapi import APIRouter

from app.api.routes.register import check
from app.api.routes.register import login
from app.api.routes.register import register
from app.api.routes.register import sign_in
from app.api.routes.register import validate

router = APIRouter(prefix="/register")

router.include_router(check.router)
router.include_router(login.router)
router.include_router(register.router)
router.include_router(sign_in.router)
router.include_router(validate.router)