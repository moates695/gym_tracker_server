import os
from dotenv import load_dotenv

load_dotenv(override=True)

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.routes.register import router as register_router
from app.api.routes import auth
from app.api.routes.workout import router as workout_router
from app.api.routes import muscles
from app.api.routes.users import router as users_router
from app.api.routes.exercises import router as exercises_router
from app.api.routes.stats import router as stats_router

from app.api.middleware.misc import SafeError

app = FastAPI(title="Gym Tracker API")

@app.exception_handler(SafeError)
async def safe_error_handler(_, exc: SafeError):
    return JSONResponse(
        status_code=400,
        content={
            "message": str(exc)
        },
    )

@app.exception_handler(Exception)
async def generic_error_handler(_, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "message": "server error"
        },
    )

@app.get("/")
async def root():
    return JSONResponse(content={"message": "OK"}, status_code=200)

app.include_router(register_router.router)
app.include_router(auth.router)
app.include_router(exercises_router.router)
app.include_router(workout_router.router)
app.include_router(muscles.router)
app.include_router(users_router.router)
app.include_router(stats_router.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, log_level='debug', reload=True)