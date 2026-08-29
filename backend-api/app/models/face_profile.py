import uuid
from sqlalchemy import Column, String, Text, Boolean, TIMESTAMP, ForeignKey, Numeric, text
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class FaceProfile(Base):
    __tablename__ = "face_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    face_image_url = Column(Text, nullable=False)
    face_image_data = Column(Text)
    qdrant_vector_id = Column(String(255))
    embedding_data = Column(Text)
    embedding_version = Column(String(50))
    enrollment_quality_score = Column(Numeric(5, 2))
    is_primary = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
