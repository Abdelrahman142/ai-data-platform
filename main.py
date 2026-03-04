from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api import auth, dataset
import os

app = FastAPI(title="Data Preparation Platform API")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(dataset.router, prefix="/datasets", tags=["Datasets"])

@app.get("/")
def root():
    return FileResponse("static/index.html")
