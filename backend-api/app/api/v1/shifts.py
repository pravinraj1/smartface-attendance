import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.models.user import User
from app.models.shift import Shift
from app.models.employee import Employee
from app.schemas.shift import ShiftCreate, ShiftUpdate, ShiftResponse
from app.services.audit import record_audit

router = APIRouter(prefix="/shifts", tags=["Shifts"])


def _validate_shift(shift_name: Optional[str], start_time, end_time, standard_hours, grace_period):
    if shift_name is not None and not str(shift_name).strip():
        raise HTTPException(status_code=400, detail="Shift name is required")
    if start_time is None or end_time is None:
        raise HTTPException(status_code=400, detail="Both start and end time are required")
    if start_time == end_time:
        raise HTTPException(status_code=400, detail="Start time and end time cannot be identical")
    if standard_hours is not None and standard_hours < 0:
        raise HTTPException(status_code=400, detail="Standard hours cannot be negative")
    if grace_period is not None and grace_period < 0:
        raise HTTPException(status_code=400, detail="Grace period cannot be negative")


@router.get("", response_model=list[ShiftResponse])
async def get_shifts(
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Shift).order_by(Shift.start_time.asc())
    if is_active is not None:
        query = query.where(Shift.is_active == is_active)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{shift_id}", response_model=ShiftResponse)
async def get_shift(
    shift_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    shift = (await db.execute(select(Shift).where(Shift.id == shift_id))).scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    return shift


@router.post("", response_model=ShiftResponse, status_code=status.HTTP_201_CREATED)
async def create_shift(
    data: ShiftCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    _validate_shift(data.shift_name, data.start_time, data.end_time, data.standard_hours, data.grace_period)
    existing = (await db.execute(select(Shift).where(Shift.shift_name == data.shift_name))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Shift with this name already exists")

    shift = Shift(**data.model_dump())
    db.add(shift)
    await db.commit()
    await db.refresh(shift)
    await record_audit(
        db, user_id=current_user.id, action="CREATE", entity_name="shift",
        entity_id=shift.id, new_value={"shift_name": shift.shift_name},
    )
    await db.commit()
    return shift


@router.put("/{shift_id}", response_model=ShiftResponse)
async def update_shift(
    shift_id: uuid.UUID,
    data: ShiftUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    shift = (await db.execute(select(Shift).where(Shift.id == shift_id))).scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    update_data = data.model_dump(exclude_unset=True)
    new_name = update_data.get("shift_name", shift.shift_name)
    new_start = update_data.get("start_time", shift.start_time)
    new_end = update_data.get("end_time", shift.end_time)
    new_std = update_data.get("standard_hours", shift.standard_hours)
    new_grace = update_data.get("grace_period", shift.grace_period)
    _validate_shift(new_name, new_start, new_end, new_std, new_grace)

    if new_name != shift.shift_name:
        dup = (await db.execute(select(Shift).where(Shift.shift_name == new_name))).scalar_one_or_none()
        if dup and dup.id != shift.id:
            raise HTTPException(status_code=400, detail="Shift with this name already exists")

    for key, value in update_data.items():
        setattr(shift, key, value)
    await db.commit()
    await db.refresh(shift)
    await record_audit(
        db, user_id=current_user.id, action="UPDATE", entity_name="shift",
        entity_id=shift.id, old_value={"shift_name": shift.shift_name}, new_value=update_data,
    )
    await db.commit()
    return shift


@router.delete("/{shift_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shift(
    shift_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    shift = (await db.execute(select(Shift).where(Shift.id == shift_id))).scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    # Unassign the shift from employees before removing it.
    await db.execute(
        Employee.__table__.update().where(Employee.shift_id == shift_id).values(shift_id=None)
    )
    await record_audit(
        db, user_id=current_user.id, action="DELETE", entity_name="shift",
        entity_id=shift.id, old_value={"shift_name": shift.shift_name},
    )
    await db.delete(shift)
    await db.commit()
