from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "SmartFace AI Service"
    VERSION: str = "1.0.0"
    
    BACKEND_API_URL: str = "http://localhost:8000"
    
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "employee_face_embeddings"
    
    FACE_MATCH_THRESHOLD: float = 0.75
    EMBEDDING_DIMENSION: int = 512
    
    RETINAFACE_CONFIDENCE: float = 0.9
    ARCFACE_MODEL: str = "arcface_r100_v1"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
