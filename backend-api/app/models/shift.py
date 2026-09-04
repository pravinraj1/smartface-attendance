import uuid
from sqlalchemy import Column, String, Text, Boolean, TIMESTAMP, Integer, Time, Numeric, text
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class Shift(Base):
    __tablename__ = "shifts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shift_name = Column(String(100), unique=True, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    standard_hours = Column(Numeric(6, 2), default=8.0)
    grace_period = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
