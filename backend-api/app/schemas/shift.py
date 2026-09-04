import uuid
from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from datetime import datetime, time


class ShiftBase(BaseModel):
    shift_name: str = Field(..., min_length=1, max_length=100)
    start_time: time
    end_time: time
    standard_hours: Decimal = Field(default=Decimal("8.0"), ge=0)
    grace_period: int = Field(default=0, ge=0)
    is_active: bool = True


class ShiftCreate(ShiftBase):
    pass


class ShiftUpdate(BaseModel):
    shift_name: Optional[str] = Field(None, min_length=1, max_length=100)
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    standard_hours: Optional[Decimal] = Field(None, ge=0)
    grace_period: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ShiftResponse(ShiftBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AssignShiftRequest(BaseModel):
    shift_id: Optional[uuid.UUID] = None
