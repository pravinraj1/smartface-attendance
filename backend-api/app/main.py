from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os

from app.core.config import settings
from app.core.database import engine, Base
from app.api import api_router_v1


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    os.makedirs(settings.STORAGE_PATH, exist_ok=True)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage_path = os.path.abspath(settings.STORAGE_PATH)
if os.path.isdir(storage_path):
    app.mount("/storage", StaticFiles(directory=storage_path), name="storage")

admin_dist = os.path.join(os.path.dirname(__file__), "..", "..", "admin-dist")
if os.path.isdir(admin_dist):
    app.mount("/admin/assets", StaticFiles(directory=os.path.join(admin_dist, "assets")), name="admin-assets")

app.include_router(api_router_v1)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.VERSION}


if os.path.isdir(admin_dist):
    @app.get("/admin/{full_path:path}")
    async def serve_admin(full_path: str):
        file_path = os.path.join(admin_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(admin_dist, "index.html"))

    @app.get("/")
    async def root():
        return FileResponse(os.path.join(admin_dist, "index.html"))
