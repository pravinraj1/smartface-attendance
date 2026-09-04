import uuid
from sqlalchemy import Column, String, Text, TIMESTAMP, ForeignKey, Date, Integer, Time, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class Attendance(Base):
    __tablename__ = "attendance"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    attendance_date = Column(Date, nullable=False)
    shift_id = Column(UUID(as_uuid=True), ForeignKey("shifts.id"))
    scheduled_start = Column(Time)
    scheduled_end = Column(Time)
    check_in = Column(TIMESTAMP)
    check_out = Column(TIMESTAMP)
    total_work_minutes = Column(Integer, default=0)
    normal_work_minutes = Column(Integer, default=0)
    overtime_minutes = Column(Integer, default=0)
    attendance_status = Column(String(20))
    late_minutes = Column(Integer, default=0)
    early_exit_minutes = Column(Integer, default=0)
    remarks = Column(Text)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    
    __table_args__ = (
        UniqueConstraint('employee_id', 'attendance_date', name='uq_employee_attendance_date'),
    )
