import uuid
from sqlalchemy import Column, String, Text, Boolean, TIMESTAMP, ForeignKey, Numeric, text
from app.core.database import Base


class FaceProfile(Base):
    __tablename__ = "face_profiles"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = Column(String(36), ForeignKey("employees.id"), nullable=False)
    face_image_url = Column(Text, nullable=False)
    qdrant_vector_id = Column(String(255))
    embedding_version = Column(String(50))
    enrollment_quality_score = Column(Numeric(5, 2))
    is_primary = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
