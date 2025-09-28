import os
from app.api.middleware.misc import load_env_vars

load_env_vars()

from fastapi import FastAPI

from app.api.routes import register
from app.api.routes import auth
from app.api.routes import exercises
from app.api.routes import workout
from app.api.routes import muscles
from app.api.routes import users
from app.api.routes import stats

app = FastAPI(title="Gym Tracker API")

app.include_router(register.router)
app.include_router(auth.router)
app.include_router(exercises.router)
app.include_router(workout.router)
app.include_router(muscles.router)
app.include_router(users.router)
app.include_router(stats.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, log_level='debug', reload=True)