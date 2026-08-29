import uuid
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime, date
from decimal import Decimal


EmploymentStatus = Literal["ACTIVE", "INACTIVE", "TERMINATED", "ON_LEAVE"]


class EmployeeBase(BaseModel):
    employee_code: str = Field(..., min_length=1, max_length=50)
    full_name: str = Field(..., min_length=1, max_length=255)
    mobile_number: Optional[str] = Field(None, max_length=20)
    department_id: Optional[uuid.UUID] = None
    monthly_salary: Optional[Decimal] = Field(None, ge=0)
    joining_date: Optional[date] = None
    employment_status: Optional[EmploymentStatus] = "ACTIVE"
    notes: Optional[str] = None


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    mobile_number: Optional[str] = Field(None, max_length=20)
    department_id: Optional[uuid.UUID] = None
    monthly_salary: Optional[Decimal] = Field(None, ge=0)
    employment_status: Optional[EmploymentStatus] = None
    face_enrolled: Optional[bool] = None
    notes: Optional[str] = None


class EmployeeResponse(EmployeeBase):
    id: uuid.UUID
    face_enrolled: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class EmployeeListResponse(BaseModel):
    employees: list[EmployeeResponse]
    total: int
    page: int
    page_size: int
