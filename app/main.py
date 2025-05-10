from dotenv import load_dotenv
import os

os.environ.clear()
load_dotenv()

from fastapi import FastAPI

from api.routes import register
from api.routes import auth
from api.routes import exercises

app = FastAPI(title="Gym Tracker API")

app.include_router(register.router)
app.include_router(auth.router)
app.include_router(exercises.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level='debug')