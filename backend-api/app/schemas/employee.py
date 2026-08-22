from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from decimal import Decimal


class EmployeeBase(BaseModel):
    employee_code: str
    full_name: str
    mobile_number: Optional[str] = None
    department_id: Optional[str] = None
    monthly_salary: Optional[Decimal] = None
    joining_date: Optional[date] = None
    employment_status: Optional[str] = "ACTIVE"
    notes: Optional[str] = None


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = None
    mobile_number: Optional[str] = None
    department_id: Optional[str] = None
    monthly_salary: Optional[Decimal] = None
    employment_status: Optional[str] = None
    face_enrolled: Optional[bool] = None
    notes: Optional[str] = None


class EmployeeResponse(EmployeeBase):
    id: str
    face_enrolled: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class EmployeeListResponse(BaseModel):
    employees: list[EmployeeResponse]
    total: int
    page: int
    page_size: int
