import uuid
from sqlalchemy import Column, String, Text, TIMESTAMP, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class ReportExport(Base):
    __tablename__ = "report_exports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    generated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    report_type = Column(String(50))
    file_url = Column(Text)
    generated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
