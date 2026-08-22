import uuid
from sqlalchemy import Column, String, Text, TIMESTAMP, ForeignKey, text
from app.core.database import Base


class ReportExport(Base):
    __tablename__ = "report_exports"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    generated_by = Column(String(36), ForeignKey("users.id"))
    report_type = Column(String(50))
    file_url = Column(Text)
    generated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
