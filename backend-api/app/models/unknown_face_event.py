import uuid
from sqlalchemy import Column, String, Text, TIMESTAMP, Numeric, Boolean, text
from app.core.database import Base


class UnknownFaceEvent(Base):
    __tablename__ = "unknown_face_events"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    snapshot_url = Column(Text)
    confidence_score = Column(Numeric(5, 2))
    detected_at = Column(TIMESTAMP)
    reviewed = Column(Boolean, default=False)
    notes = Column(Text)
