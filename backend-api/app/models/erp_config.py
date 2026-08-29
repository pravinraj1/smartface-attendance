import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class ERPConfig(Base):
    __tablename__ = "erp_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    erp_name = Column(String(100), nullable=False, default="Custom ERP")
    erp_url = Column(String(500), nullable=False)
    api_key = Column(String(200), nullable=True)
    auth_type = Column(String(50), nullable=False, default="api_key")
    data_format = Column(String(20), nullable=False, default="xml")
    sync_enabled = Column(Boolean, default=True)
    sync_interval_minutes = Column(Integer, default=15)
    last_sync_at = Column(DateTime, nullable=True)
    last_sync_status = Column(String(50), nullable=True)
    last_sync_message = Column(Text, nullable=True)
    endpoint_attendance = Column(String(500), nullable=True)
    endpoint_employees = Column(String(500), nullable=True)
    webhook_url = Column(String(500), nullable=True)
    webhook_secret = Column(String(200), nullable=True)
    webhook_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ERPsyncLog(Base):
    __tablename__ = "erp_sync_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    erp_config_id = Column(UUID(as_uuid=True), ForeignKey("erp_configs.id"), nullable=False)
    sync_type = Column(String(50), nullable=False)
    direction = Column(String(20), nullable=False, default="push")
    status = Column(String(50), nullable=False, default="pending")
    records_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    request_payload = Column(Text, nullable=True)
    response_payload = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
