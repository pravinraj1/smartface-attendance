from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date


class AttendanceBase(BaseModel):
    employee_id: str
    attendance_date: date
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    total_work_minutes: int = 0
    attendance_status: Optional[str] = None
    late_minutes: int = 0
    early_exit_minutes: int = 0
    remarks: Optional[str] = None


class AttendanceCreate(AttendanceBase):
    pass


class AttendanceUpdate(BaseModel):
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    attendance_status: Optional[str] = None
    remarks: Optional[str] = None


class AttendanceResponse(AttendanceBase):
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AttendanceLogBase(BaseModel):
    employee_id: Optional[str] = None
    event_type: str
    event_time: datetime
    confidence_score: Optional[float] = None
    snapshot_url: Optional[str] = None
    recognition_status: str


class AttendanceLogResponse(AttendanceLogBase):
    id: str
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CheckInRequest(BaseModel):
    employee_id: str
    confidence_score: float
    snapshot_url: Optional[str] = None


class CheckOutRequest(BaseModel):
    employee_id: str
    confidence_score: float
    snapshot_url: Optional[str] = None


class AttendanceDecisionResponse(BaseModel):
    action: str
    employee_id: str
    employee_name: str
    timestamp: datetime
    message: str
