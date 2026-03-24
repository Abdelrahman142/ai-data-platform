from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api import auth, dataset, ai, collaboration
import os

from contextlib import asynccontextmanager
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Memory Cache on startup
    FastAPICache.init(InMemoryBackend())
    yield

app = FastAPI(title="Data Preparation Platform API", lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(dataset.router, prefix="/datasets", tags=["Datasets"])
app.include_router(ai.router, prefix="/ai", tags=["AI Integration"])
app.include_router(collaboration.router, prefix="/collaboration", tags=["Collaboration"])

@app.get("/")
def root():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001)) # Default to 8001 to avoid conflicts
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
