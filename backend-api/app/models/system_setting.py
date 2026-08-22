import uuid
from sqlalchemy import Column, String, Text, TIMESTAMP, UniqueConstraint, text
from app.core.database import Base


class SystemSetting(Base):
    __tablename__ = "system_settings"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    setting_key = Column(String(255), unique=True)
    setting_value = Column(Text)
    description = Column(Text)
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
