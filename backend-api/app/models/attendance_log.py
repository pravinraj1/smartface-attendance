import uuid
from sqlalchemy import Column, String, Text, TIMESTAMP, ForeignKey, Numeric, text
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"))
    event_type = Column(String(20))
    event_time = Column(TIMESTAMP, nullable=False)
    confidence_score = Column(Numeric(5, 2))
    snapshot_url = Column(Text)
    recognition_status = Column(String(20))
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
