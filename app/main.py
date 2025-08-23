import os
from api.middleware.misc import load_env_vars

load_env_vars()

from fastapi import FastAPI

from api.routes import register
from api.routes import auth
from api.routes import exercises
from api.routes import workout
from api.routes import muscles
from api.routes import users

app = FastAPI(title="Gym Tracker API")

app.include_router(register.router)
app.include_router(auth.router)
app.include_router(exercises.router)
app.include_router(workout.router)
app.include_router(muscles.router)
app.include_router(users.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level='debug')