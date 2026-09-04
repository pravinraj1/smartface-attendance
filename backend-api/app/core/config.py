import secrets
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "SmartFace Attendance Management System"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    SUPABASE_URL: str = ""
    SUPABASE_PUBLISHABLE_KEY: str = ""
    SUPABASE_SECRET_KEY: str = ""

    DATABASE_URL: str = ""

    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    ADMIN_EMAIL: str = "admin@smartface.com"
    ADMIN_INITIAL_PASSWORD: str = ""
    RATE_LIMIT_LOGIN: int = 10
    RATE_LIMIT_WINDOW: int = 60
    MAX_REQUEST_BODY_BYTES: int = 3 * 1024 * 1024
    DOCS_ENABLED: bool = True

    FACE_MATCH_THRESHOLD: float = 0.75
    FACE_DUPLICATE_THRESHOLD: float = 0.85
    FACE_SERVICE_URL: str = ""
    ATTENDANCE_COOLDOWN_MINUTES: int = 5
    CHECKIN_START_TIME: str = "08:00"
    LATE_AFTER_TIME: str = "09:15"
    AUTO_CHECKOUT_TIME: str = "22:00"
    AUTO_CHECKOUT_ENABLED: bool = True
    STANDARD_WORKING_HOURS: int = 8

    STORAGE_PATH: str = "./storage"

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()

if not settings.SECRET_KEY:
    settings.SECRET_KEY = secrets.token_urlsafe(64)

if settings.DATABASE_URL.startswith("postgresql://"):
    settings.DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

if "sslmode=" in settings.DATABASE_URL:
    settings.DATABASE_URL = settings.DATABASE_URL.split("?")[0]
