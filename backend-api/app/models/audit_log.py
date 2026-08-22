import uuid
from sqlalchemy import Column, String, Text, TIMESTAMP, ForeignKey, text
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"))
    action = Column(String(255))
    entity_name = Column(String(100))
    entity_id = Column(String(36))
    old_value = Column(Text)
    new_value = Column(Text)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
