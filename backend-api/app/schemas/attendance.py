import uuid
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime, date, time


AttendanceStatus = Literal["PRESENT", "ABSENT", "LATE", "LEAVE", "HOLIDAY", "WEEKEND"]
EventType = Literal["CHECK_IN", "CHECK_OUT"]


class AttendanceBase(BaseModel):
    employee_id: uuid.UUID
    attendance_date: date
    shift_id: Optional[uuid.UUID] = None
    scheduled_start: Optional[time] = None
    scheduled_end: Optional[time] = None
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    total_work_minutes: int = Field(default=0, ge=0)
    normal_work_minutes: int = Field(default=0, ge=0)
    overtime_minutes: int = Field(default=0, ge=0)
    attendance_status: Optional[AttendanceStatus] = None
    late_minutes: int = Field(default=0, ge=0)
    early_exit_minutes: int = Field(default=0, ge=0)
    remarks: Optional[str] = None


class AttendanceCreate(AttendanceBase):
    pass


class AttendanceUpdate(BaseModel):
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    attendance_status: Optional[AttendanceStatus] = None
    remarks: Optional[str] = None


class AttendanceResponse(AttendanceBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AttendanceLogBase(BaseModel):
    employee_id: Optional[uuid.UUID] = None
    event_type: EventType
    event_time: datetime
    confidence_score: Optional[float] = Field(None, ge=0, le=1)
    snapshot_url: Optional[str] = None
    recognition_status: str


class AttendanceLogResponse(AttendanceLogBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CheckInRequest(BaseModel):
    employee_id: uuid.UUID
    confidence_score: float = Field(..., ge=0, le=1)
    snapshot_url: Optional[str] = None


class CheckOutRequest(BaseModel):
    employee_id: uuid.UUID
    confidence_score: float = Field(..., ge=0, le=1)
    snapshot_url: Optional[str] = None


class AttendanceDecisionResponse(BaseModel):
    action: str
    employee_id: uuid.UUID
    employee_name: str
    timestamp: datetime
    message: str
