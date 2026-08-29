import uuid
from sqlalchemy import Column, String, Text, TIMESTAMP, ForeignKey, Boolean, text
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class LeaveType(Base):
    __tablename__ = "leave_types"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    leave_name = Column(String(100))
    is_paid = Column(Boolean, default=True)
