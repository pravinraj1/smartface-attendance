from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.vector_db import init_collection
from app.api.face_routes import router as face_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_collection()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(face_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.VERSION}
