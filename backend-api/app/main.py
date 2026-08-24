from fastapi import FastAPI, Request
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
    from app.core.database import async_session
    from app.models.user import User
    from app.core.security import get_password_hash
    from sqlalchemy import select
    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == "admin@smartface.com"))
        if not result.scalar_one_or_none():
            admin = User(
                email="admin@smartface.com",
                full_name="Admin",
                password_hash=get_password_hash("Admin123!"),
                is_active=True,
            )
            session.add(admin)
            await session.commit()
            print("Seeded admin user: admin@smartface.com / Admin123!")
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
os.makedirs(storage_path, exist_ok=True)
app.mount("/storage", StaticFiles(directory=storage_path), name="storage")

app.include_router(api_router_v1)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.VERSION}


admin_dist = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "admin-dist"))

if os.path.isdir(admin_dist):
    admin_assets = os.path.join(admin_dist, "assets")
    if os.path.isdir(admin_assets):
        app.mount("/assets", StaticFiles(directory=admin_assets), name="admin-assets")

    SPA_PREFIXES = ("api/", "storage/", "health", "docs", "openapi.json", "redoc")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith(SPA_PREFIXES):
            return
        file_path = os.path.join(admin_dist, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(admin_dist, "index.html"))
