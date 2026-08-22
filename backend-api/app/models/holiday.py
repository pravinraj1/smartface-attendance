import uuid
from sqlalchemy import Column, String, Text, TIMESTAMP, Date, text
from app.core.database import Base


class Holiday(Base):
    __tablename__ = "holidays"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    holiday_name = Column(String(255))
    holiday_date = Column(Date)
    description = Column(Text)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
