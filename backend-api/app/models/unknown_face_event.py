import uuid
from sqlalchemy import Column, String, Text, TIMESTAMP, Numeric, Boolean, text
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class UnknownFaceEvent(Base):
    __tablename__ = "unknown_face_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_url = Column(Text)
    confidence_score = Column(Numeric(5, 2))
    detected_at = Column(TIMESTAMP)
    reviewed = Column(Boolean, default=False)
    notes = Column(Text)
