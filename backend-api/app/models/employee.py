import uuid
from sqlalchemy import Column, String, Text, Boolean, TIMESTAMP, ForeignKey, Numeric, Date, Integer, text
from app.core.database import Base


class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_code = Column(String(50), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    mobile_number = Column(String(20), unique=True)
    department_id = Column(String(36), ForeignKey("departments.id"))
    monthly_salary = Column(Numeric(12, 2))
    joining_date = Column(Date)
    employment_status = Column(String(20), default="ACTIVE")
    face_enrolled = Column(Boolean, default=False)
    notes = Column(Text)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
