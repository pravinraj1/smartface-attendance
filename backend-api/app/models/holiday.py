import uuid
from sqlalchemy import Column, String, Text, TIMESTAMP, Date, text
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class Holiday(Base):
    __tablename__ = "holidays"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    holiday_name = Column(String(255))
    holiday_date = Column(Date)
    description = Column(Text)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
