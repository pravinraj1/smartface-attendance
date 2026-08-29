import uuid
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal


class FaceProfileBase(BaseModel):
    employee_id: uuid.UUID
    face_image_url: str
    qdrant_vector_id: Optional[str] = None
    embedding_version: Optional[str] = None
    enrollment_quality_score: Optional[Decimal] = None
    is_primary: bool = True
    face_image_data: Optional[str] = None
    embedding_data: Optional[str] = None


class FaceProfileCreate(FaceProfileBase):
    pass


class FaceProfileResponse(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    face_image_url: str
    qdrant_vector_id: Optional[str] = None
    embedding_version: Optional[str] = None
    enrollment_quality_score: Optional[Decimal] = None
    is_primary: bool = True
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class FaceEnrollRequest(BaseModel):
    employee_id: str
    face_images: list[str]


class FaceVerifyRequest(BaseModel):
    face_image: str


class FaceVerifyResponse(BaseModel):
    matched: bool
    employee_id: Optional[uuid.UUID] = None
    employee_name: Optional[str] = None
    confidence: float
