from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
import os
import secrets
import time

from app.core.config import settings
from app.core.database import engine, Base
from app.core.logging_config import get_logger
from app.api import api_router_v1

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.STORAGE_PATH, exist_ok=True)
    logger.info("Starting SmartFace API", extra={"event": "startup"})
    
    from app.core.database import async_session
    from app.models.user import User
    from app.core.security import get_password_hash
    from sqlalchemy import select
    
    try:
        async with async_session() as session:
            # Seed admin user if not exists (tables created by Alembic migration)
            result = await session.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
            if not result.scalar_one_or_none():
                admin_pass = settings.ADMIN_INITIAL_PASSWORD or secrets.token_urlsafe(16)
                from app.models.role import Role
                super_admin = (await session.execute(
                    select(Role).where(Role.role_name == "SUPER_ADMIN")
                )).scalar_one_or_none()
                admin = User(
                    email=settings.ADMIN_EMAIL,
                    full_name="Admin",
                    password_hash=get_password_hash(admin_pass),
                    role_id=super_admin.id if super_admin else None,
                    is_active=True,
                )
                session.add(admin)
                await session.commit()
                logger.info("Seeded initial admin user", extra={"event": "admin_seed"})
            else:
                logger.info("Initial admin user already present", extra={"event": "admin_seed"})
    except Exception as e:
        logger.warning(f"Startup seed warning: {e}", extra={"event": "admin_seed"})
    
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DOCS_ENABLED else None,
    redoc_url="/redoc" if settings.DOCS_ENABLED else None,
    openapi_url="/openapi.json" if settings.DOCS_ENABLED else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Request body size limit ---
class BodySizeLimitMiddleware:
    def __init__(self, app, max_bytes):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        content_length = 0
        for key, value in scope.get("headers", []):
            if key == b"content-length":
                try:
                    content_length = int(value)
                except ValueError:
                    content_length = 0
        if content_length > self.max_bytes:
            response = JSONResponse(status_code=413, content={"detail": "Request body too large"})
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)

app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.MAX_REQUEST_BODY_BYTES)

# --- Login rate limiting ---
_login_attempts = {}

class LoginRateLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if path.endswith("/auth/login"):
            client = scope.get("client")
            ip = client[0] if client else "unknown"
            now = time.time()
            window = settings.RATE_LIMIT_WINDOW
            limit = settings.RATE_LIMIT_LOGIN
            if len(_login_attempts) > 10000:
                for stale_ip in [k for k, v in _login_attempts.items() if not v or now - v[-1] >= window]:
                    _login_attempts.pop(stale_ip, None)
            entry = [t for t in _login_attempts.get(ip, []) if now - t < window]
            _login_attempts[ip] = entry
            if len(entry) >= limit:
                response = JSONResponse(status_code=429, content={"detail": "Too many login attempts"})
                response.headers["Retry-After"] = str(window)
                await response(scope, receive, send)
                return

            orig_send = send
            async def counting_send(message):
                if message["type"] == "http.response.start":
                    if message.get("status", 0) != 200:
                        _login_attempts[ip].append(time.time())
                await orig_send(message)

            await self.app(scope, receive, counting_send)
            return
        await self.app(scope, receive, send)

app.add_middleware(LoginRateLimitMiddleware)

# --- Security headers ---
class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def add_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-content-type-options", b"nosniff"))
                headers.append((b"x-frame-options", b"SAMEORIGIN"))
                headers.append((b"referrer-policy", b"no-referrer"))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, add_headers)

app.add_middleware(SecurityHeadersMiddleware)

# --- Structured request logging ---
import asyncio as _asyncio

class RequestLogMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        start = time.time()
        path = scope.get("path", "")
        method = scope.get("method", "")
        client = scope.get("client")
        ip = client[0] if client else "unknown"

        orig_send = send

        async def logging_send(message):
            if message["type"] == "http.response.start":
                status = message.get("status", 0)
                duration_ms = int((time.time() - start) * 1000)
                logger.info(
                    "request",
                    extra={
                        "event": "request",
                        "method": method,
                        "path": path,
                        "status_code": status,
                        "ip": ip,
                        "duration_ms": duration_ms,
                    },
                )
            await orig_send(message)

        await self.app(scope, receive, logging_send)

app.add_middleware(RequestLogMiddleware)

storage_path = os.path.abspath(settings.STORAGE_PATH)
os.makedirs(storage_path, exist_ok=True)
app.mount("/storage", StaticFiles(directory=storage_path), name="storage")

app.include_router(api_router_v1)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.VERSION}


admin_dist = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "admin-dist"))
admin_dist_real = os.path.realpath(admin_dist)

if os.path.isdir(admin_dist):
    admin_assets = os.path.join(admin_dist, "assets")
    if os.path.isdir(admin_assets):
        app.mount("/assets", StaticFiles(directory=admin_assets), name="admin-assets")

    SPA_PREFIXES = ("api/", "storage/", "health", "docs", "openapi.json", "redoc")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith(SPA_PREFIXES):
            raise HTTPException(status_code=404, detail="Not found")
        file_path = os.path.join(admin_dist, full_path)
        if full_path and os.path.isfile(file_path):
            real = os.path.realpath(file_path)
            if real.startswith(admin_dist_real + os.sep):
                return FileResponse(file_path)
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(os.path.join(admin_dist, "index.html"))
