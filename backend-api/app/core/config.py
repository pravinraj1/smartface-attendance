from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    PROJECT_NAME: str = "SmartFace Attendance Management System"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    DATABASE_URL: str = "sqlite+aiosqlite:///./smartface_attendance.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    SECRET_KEY: str = "smartface-production-secret-key-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    CORS_ORIGINS: List[str] = ["*"]
    
    FACE_MATCH_THRESHOLD: float = 0.75
    ATTENDANCE_COOLDOWN_MINUTES: int = 5
    CHECKIN_START_TIME: str = "08:00"
    LATE_AFTER_TIME: str = "09:15"
    AUTO_CHECKOUT_TIME: str = "22:00"
    
    STORAGE_PATH: str = "./storage"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

if settings.DATABASE_URL.startswith("postgresql://"):
    settings.DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
