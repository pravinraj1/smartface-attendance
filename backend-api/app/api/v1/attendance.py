from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime, date

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.attendance import Attendance
from app.models.attendance_log import AttendanceLog
from app.models.employee import Employee
from app.schemas.attendance import (
    AttendanceResponse,
    AttendanceLogResponse,
    CheckInRequest,
    CheckOutRequest,
    AttendanceDecisionResponse,
)

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.get("", response_model=list[AttendanceResponse])
async def get_attendance(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    employee_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Attendance)
    
    if employee_id:
        query = query.where(Attendance.employee_id == employee_id)
    if start_date:
        query = query.where(Attendance.attendance_date >= start_date)
    if end_date:
        query = query.where(Attendance.attendance_date <= end_date)
    if status:
        query = query.where(Attendance.attendance_status == status)
    
    query = query.order_by(Attendance.attendance_date.desc())
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/employee/{employee_id}", response_model=list[AttendanceResponse])
async def get_employee_attendance(
    employee_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Attendance).where(Attendance.employee_id == employee_id)
    
    if start_date:
        query = query.where(Attendance.attendance_date >= start_date)
    if end_date:
        query = query.where(Attendance.attendance_date <= end_date)
    
    query = query.order_by(Attendance.attendance_date.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/today", response_model=list[AttendanceResponse])
async def get_today_attendance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    result = await db.execute(
        select(Attendance).where(Attendance.attendance_date == today)
    )
    return result.scalars().all()


@router.get("/stats")
async def get_attendance_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    
    total_employees = await db.execute(
        select(func.count(Employee.id)).where(Employee.employment_status == "ACTIVE")
    )
    total = total_employees.scalar()
    
    present_today = await db.execute(
        select(func.count(Attendance.id)).where(
            Attendance.attendance_date == today,
            Attendance.attendance_status.in_(["PRESENT", "LATE"])
        )
    )
    present = present_today.scalar()
    
    late_today = await db.execute(
        select(func.count(Attendance.id)).where(
            Attendance.attendance_date == today,
            Attendance.attendance_status == "LATE"
        )
    )
    late = late_today.scalar()
    
    return {
        "total_employees": total,
        "present_today": present,
        "absent_today": total - present,
        "late_today": late,
    }


@router.post("/checkin", response_model=AttendanceDecisionResponse)
async def check_in(
    request: CheckInRequest,
    db: AsyncSession = Depends(get_db),
):
    employee_result = await db.execute(
        select(Employee).where(Employee.id == request.employee_id)
    )
    employee = employee_result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if employee.employment_status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Employee is not active")
    
    today = date.today()
    now = datetime.utcnow()
    
    existing_attendance = await db.execute(
        select(Attendance).where(
            Attendance.employee_id == request.employee_id,
            Attendance.attendance_date == today,
        )
    )
    attendance = existing_attendance.scalar_one_or_none()
    
    if attendance and attendance.check_out:
        raise HTTPException(status_code=400, detail="Already checked out today")
    
    if attendance and attendance.check_in:
        raise HTTPException(status_code=400, detail="Already checked in today")
    
    if not attendance:
        attendance = Attendance(
            employee_id=request.employee_id,
            attendance_date=today,
            check_in=now,
            attendance_status="PRESENT",
        )
        db.add(attendance)
    else:
        attendance.check_in = now
        attendance.attendance_status = "PRESENT"
    
    log = AttendanceLog(
        employee_id=request.employee_id,
        event_type="CHECK_IN",
        event_time=now,
        confidence_score=request.confidence_score,
        snapshot_url=request.snapshot_url,
        recognition_status="SUCCESS",
    )
    db.add(log)
    
    await db.commit()
    await db.refresh(attendance)
    
    return AttendanceDecisionResponse(
        action="CHECK_IN",
        employee_id=employee.id,
        employee_name=employee.full_name,
        timestamp=now,
        message=f"Check-in recorded for {employee.full_name}",
    )


@router.post("/checkout", response_model=AttendanceDecisionResponse)
async def check_out(
    request: CheckOutRequest,
    db: AsyncSession = Depends(get_db),
):
    employee_result = await db.execute(
        select(Employee).where(Employee.id == request.employee_id)
    )
    employee = employee_result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    today = date.today()
    now = datetime.utcnow()
    
    existing_attendance = await db.execute(
        select(Attendance).where(
            Attendance.employee_id == request.employee_id,
            Attendance.attendance_date == today,
        )
    )
    attendance = existing_attendance.scalar_one_or_none()
    
    if not attendance:
        raise HTTPException(status_code=400, detail="No check-in record found for today")
    
    if attendance.check_out:
        raise HTTPException(status_code=400, detail="Already checked out today")
    
    attendance.check_out = now
    
    if attendance.check_in:
        work_duration = now - attendance.check_in
        attendance.total_work_minutes = int(work_duration.total_seconds() / 60)
    
    log = AttendanceLog(
        employee_id=request.employee_id,
        event_type="CHECK_OUT",
        event_time=now,
        confidence_score=request.confidence_score,
        snapshot_url=request.snapshot_url,
        recognition_status="SUCCESS",
    )
    db.add(log)
    
    await db.commit()
    await db.refresh(attendance)
    
    return AttendanceDecisionResponse(
        action="CHECK_OUT",
        employee_id=employee.id,
        employee_name=employee.full_name,
        timestamp=now,
        message=f"Check-out recorded for {employee.full_name}",
    )


@router.get("/logs", response_model=list[AttendanceLogResponse])
async def get_attendance_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    employee_id: Optional[str] = None,
    event_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(AttendanceLog)
    
    if employee_id:
        query = query.where(AttendanceLog.employee_id == employee_id)
    if event_type:
        query = query.where(AttendanceLog.event_type == event_type)
    if start_date:
        query = query.where(AttendanceLog.event_time >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.where(AttendanceLog.event_time <= datetime.combine(end_date, datetime.max.time()))
    
    query = query.order_by(AttendanceLog.event_time.desc())
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
