import uuid
from sqlalchemy import Column, String, Text, TIMESTAMP, text
from app.core.database import Base


class Role(Base):
    __tablename__ = "roles"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    role_name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
