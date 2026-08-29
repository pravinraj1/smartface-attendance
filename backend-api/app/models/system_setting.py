import uuid
from sqlalchemy import Column, String, Text, TIMESTAMP, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class SystemSetting(Base):
    __tablename__ = "system_settings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    setting_key = Column(String(255), unique=True)
    setting_value = Column(Text)
    description = Column(Text)
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
