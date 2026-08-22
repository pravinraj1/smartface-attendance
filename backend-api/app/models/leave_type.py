import uuid
from sqlalchemy import Column, String, Text, TIMESTAMP, ForeignKey, Boolean, text
from app.core.database import Base


class LeaveType(Base):
    __tablename__ = "leave_types"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    leave_name = Column(String(100))
    is_paid = Column(Boolean, default=True)
