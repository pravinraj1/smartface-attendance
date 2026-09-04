import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.core.config import settings
from app.core.logging_config import get_logger
from app.models.user import User
from app.models.attendance import Attendance
from app.models.attendance_log import AttendanceLog
from app.models.employee import Employee
from app.models.shift import Shift
from app.schemas.attendance import (
    AttendanceResponse,
    AttendanceLogResponse,
    CheckInRequest,
    CheckOutRequest,
    AttendanceDecisionResponse,
)

router = APIRouter(prefix="/attendance", tags=["Attendance"])
logger = get_logger(__name__)

# Attendance is recorded in real local time (IST, Asia/Kolkata). The DB
# stores naive TIMESTAMP columns (no tz), so we persist the IST wall-clock
# value (local time as seen by the office) so check-in/out, dates, late
# calculation and stats all line up on the real local clock.
try:
    _TZ = ZoneInfo("Asia/Kolkata")
except Exception:  # pragma: no cover - fall back to a fixed +5:30 offset
    from datetime import timezone, timedelta as _td
    _TZ = timezone(_td(hours=5, minutes=30))


def _now_ist() -> datetime:
    """Current IST wall-clock time as a naive datetime for naive TIMESTAMP columns."""
    return datetime.now(_TZ).replace(tzinfo=None)


def _today_ist() -> date:
    return datetime.now(_TZ).date()


def _parse_time(value: str) -> Optional[time]:
    try:
        return time.fromisoformat(value)
    except ValueError:
        return None


def _standard_minutes(shift: Optional[Shift], default_hours=None) -> int:
    """Standard working duration in minutes for an employee's shift."""
    hours = default_hours
    if shift is not None and getattr(shift, "standard_hours", None) is not None:
        hours = float(shift.standard_hours)
    if hours is None:
        hours = settings.STANDARD_WORKING_HOURS
    return int(hours * 60)


def _is_overnight(shift: Optional[Shift], scheduled_start: Optional[time], scheduled_end: Optional[time]) -> bool:
    """True when a shift crosses midnight (start later than end)."""
    if scheduled_start is not None and scheduled_end is not None:
        return scheduled_start > scheduled_end
    return False


def _compute_late_minutes(check_in_dt: datetime, today: date, shift: Optional[Shift] = None,
                          scheduled_start: Optional[time] = None, scheduled_end: Optional[time] = None) -> int:
    """Late minutes based on the assigned shift (start + grace). If no shift is
    assigned, fall back to the global LATE_AFTER_TIME for backward compatibility."""
    if shift is not None and scheduled_start is not None:
        threshold = datetime.combine(today, scheduled_start)
        grace = getattr(shift, "grace_period", 0) or 0
        threshold += timedelta(minutes=grace)
        if check_in_dt > threshold:
            return int((check_in_dt - threshold).total_seconds() // 60)
        return 0

    late_after = _parse_time(settings.LATE_AFTER_TIME)
    if not late_after:
        return 0
    threshold = datetime.combine(today, late_after)
    if check_in_dt > threshold:
        return int((check_in_dt - threshold).total_seconds() // 60)
    return 0


def _compute_ot(shift: Optional[Shift], total_work_minutes: int) -> tuple[int, int]:
    """Return (normal_work_minutes, overtime_minutes) given the shift standard hours.

    OT = total - standard  (never negative). Normal = total - OT."""
    total = max(int(total_work_minutes or 0), 0)
    standard = _standard_minutes(shift)
    if total <= standard:
        return total, 0
    return standard, total - standard


def _apply_ot(rec: Attendance, shift: Optional[Shift], check_out_dt: datetime) -> None:
    if rec.check_in and check_out_dt > rec.check_in:
        total = int((check_out_dt - rec.check_in).total_seconds() // 60)
    else:
        total = 0
    rec.total_work_minutes = total
    rec.normal_work_minutes, rec.overtime_minutes = _compute_ot(shift, total)


async def _load_shift(db: AsyncSession, shift_id) -> Optional[Shift]:
    if shift_id is None:
        return None
    shift = (await db.execute(select(Shift).where(Shift.id == shift_id))).scalar_one_or_none()
    return shift


async def _maybe_auto_checkout(db: AsyncSession, employee: Employee, now: datetime) -> None:
    """Shift-aware automatic checkout.

    If the employee has an open attendance record whose scheduled shift window
    has already ended (based on that shift's end time, or AUTO_CHECKOUT_TIME as a
    fallback when no shift is assigned), close it now, computing total/normal/OT.
    This keeps stale open records from blocking the next check-in and prevents
    blindly applying one universal 22:00 cutoff to every shift."""
    if not getattr(settings, "AUTO_CHECKOUT_ENABLED", True):
        return
    open_rec = (await db.execute(
        select(Attendance).where(
            Attendance.employee_id == employee.id,
            Attendance.check_out.is_(None),
        ).order_by(Attendance.check_in.desc())
    )).scalars().first()
    if not open_rec:
        return

    shift = await _load_shift(db, open_rec.shift_id)
    end_dt: Optional[datetime] = None

    if open_rec.scheduled_end is not None:
        end_day = open_rec.attendance_date
        overnight = _is_overnight(shift, open_rec.scheduled_start, open_rec.scheduled_end)
        if overnight:
            end_day = end_day + timedelta(days=1)
        end_dt = datetime.combine(end_day, open_rec.scheduled_end)
    else:
        auto = _parse_time(settings.AUTO_CHECKOUT_TIME)
        if auto:
            end_dt = datetime.combine(open_rec.attendance_date, auto)

    if end_dt is None or now <= end_dt:
        return

    open_rec.check_out = end_dt
    _apply_ot(open_rec, shift, end_dt)
    db.add(open_rec)


def _serialize_attendance(rec: Attendance) -> dict:
    total_hours = None
    if rec.total_work_minutes and rec.total_work_minutes > 0:
        total_hours = round(rec.total_work_minutes / 60, 2)
    return {
        "id": str(rec.id),
        "employee_id": str(rec.employee_id),
        "date": str(rec.attendance_date),
        "shift_id": str(rec.shift_id) if rec.shift_id else None,
        "scheduled_start": rec.scheduled_start.isoformat() if rec.scheduled_start else None,
        "scheduled_end": rec.scheduled_end.isoformat() if rec.scheduled_end else None,
        "check_in": rec.check_in.isoformat() if rec.check_in else None,
        "check_out": rec.check_out.isoformat() if rec.check_out else None,
        "total_hours": total_hours,
        "total_work_minutes": rec.total_work_minutes or 0,
        "normal_work_minutes": rec.normal_work_minutes or 0,
        "overtime_minutes": rec.overtime_minutes or 0,
        "status": rec.attendance_status or "",
        "late_minutes": rec.late_minutes or 0,
        "remarks": rec.remarks,
    }


async def _enrich_attendance(db: AsyncSession, records: list[Attendance]) -> dict:
    emp_ids = {r.employee_id for r in records if r.employee_id}
    employees: dict = {}
    if emp_ids:
        res = await db.execute(select(Employee).where(Employee.id.in_(emp_ids)))
        employees = {e.id: e for e in res.scalars().all()}
    rows = []
    for rec in records:
        row = _serialize_attendance(rec)
        emp = employees.get(rec.employee_id)
        row["employee_name"] = emp.full_name if emp else None
        row["employee_code"] = emp.employee_code if emp else None
        rows.append(row)
    return {"attendance": rows, "total": len(rows)}


@router.get("")
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
    query = select(Attendance).order_by(Attendance.attendance_date.desc())

    if employee_id:
        try:
            emp_uuid = uuid.UUID(employee_id)
            query = query.where(Attendance.employee_id == emp_uuid)
        except ValueError:
            pass
    if start_date:
        query = query.where(Attendance.attendance_date >= start_date)
    if end_date:
        query = query.where(Attendance.attendance_date <= end_date)
    if status:
        query = query.where(Attendance.attendance_status == status)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()
    return await _enrich_attendance(db, records)


@router.get("/employee/{employee_id}", response_model=list[AttendanceResponse])
async def get_employee_attendance(
    employee_id: uuid.UUID,
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
    today = _today_ist()
    result = await db.execute(
        select(Attendance).where(Attendance.attendance_date == today)
    )
    return result.scalars().all()


@router.get("/stats")
async def get_attendance_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = _today_ist()
    
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

    checked_out_today = await db.execute(
        select(func.count(Attendance.id)).where(
            Attendance.attendance_date == today,
            Attendance.check_out.isnot(None),
        )
    )
    checked_out = checked_out_today.scalar()

    ot_today = await db.execute(
        select(func.coalesce(func.sum(Attendance.overtime_minutes), 0)).where(
            Attendance.attendance_date == today,
        )
    )
    ot_minutes = int(ot_today.scalar() or 0)

    return {
        "total_employees": total,
        "present_today": present,
        "absent_today": total - present,
        "late_today": late,
        "checked_out_today": checked_out,
        "overtime_minutes_today": ot_minutes,
        "overtime_hours_today": round(ot_minutes / 60, 2),
    }


@router.post("/checkin", response_model=AttendanceDecisionResponse)
async def check_in(
    request: CheckInRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    emp_id = uuid.UUID(request.employee_id) if isinstance(request.employee_id, str) else request.employee_id
    
    employee_result = await db.execute(
        select(Employee).where(Employee.id == emp_id)
    )
    employee = employee_result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if employee.employment_status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Employee is not active")
    
    today = _today_ist()
    now = _now_ist()

    # Shift-aware automatic checkout: close a stale open record first.
    await _maybe_auto_checkout(db, employee, now)

    shift = await _load_shift(db, employee.shift_id)
    scheduled_start = shift.start_time if shift else None
    scheduled_end = shift.end_time if shift else None

    existing_attendance = await db.execute(
        select(Attendance).where(
            Attendance.employee_id == emp_id,
            Attendance.attendance_date == today,
        )
    )
    attendance = existing_attendance.scalar_one_or_none()
    
    if attendance and attendance.check_out:
        raise HTTPException(status_code=400, detail="Already checked out today")
    
    if attendance and attendance.check_in:
        raise HTTPException(status_code=400, detail="Already checked in today")

    late_mins = _compute_late_minutes(now, today, shift, scheduled_start, scheduled_end)
    new_status = "LATE" if late_mins > 0 else "PRESENT"

    if not attendance:
        attendance = Attendance(
            employee_id=emp_id,
            attendance_date=today,
            shift_id=shift.id if shift else None,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            check_in=now,
            attendance_status=new_status,
            late_minutes=late_mins,
        )
        db.add(attendance)
    else:
        attendance.check_in = now
        attendance.shift_id = shift.id if shift else None
        attendance.scheduled_start = scheduled_start
        attendance.scheduled_end = scheduled_end
        attendance.attendance_status = new_status
        attendance.late_minutes = late_mins
    
    log = AttendanceLog(
        employee_id=emp_id,
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
    current_user: User = Depends(get_current_user),
):
    emp_id = uuid.UUID(request.employee_id) if isinstance(request.employee_id, str) else request.employee_id
    
    employee_result = await db.execute(
        select(Employee).where(Employee.id == emp_id)
    )
    employee = employee_result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    now = _now_ist()

    # Find the employee's OPEN check-in record, regardless of calendar date.
    # For overnight shifts (22:00 -> 06:00) the checkout occurs on the following
    # calendar day, so it must match the open record rather than today's date.
    open_rec = (await db.execute(
        select(Attendance).where(
            Attendance.employee_id == emp_id,
            Attendance.check_out.is_(None),
        ).order_by(Attendance.check_in.desc())
    )).scalars().first()

    if not open_rec:
        today = _today_ist()
        done_today = (await db.execute(
            select(Attendance).where(
                Attendance.employee_id == emp_id,
                Attendance.attendance_date == today,
                Attendance.check_out.isnot(None),
            )
        )).scalar_one_or_none()
        if done_today:
            raise HTTPException(status_code=400, detail="Already checked out today")
        raise HTTPException(status_code=400, detail="No check-in record found")

    attendance = open_rec

    shift = await _load_shift(db, attendance.shift_id)
    attendance.check_out = now
    _apply_ot(attendance, shift, now)
    
    log = AttendanceLog(
        employee_id=emp_id,
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
        try:
            emp_uuid = uuid.UUID(employee_id)
            query = query.where(AttendanceLog.employee_id == emp_uuid)
        except ValueError:
            pass
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


@router.get("/logs/live")
async def get_live_attendance_feed(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Real-time attendance activity feed (most recent check-in/check-out events)."""
    result = await db.execute(
        select(AttendanceLog)
        .order_by(AttendanceLog.event_time.desc())
        .limit(limit)
    )
    logs = result.scalars().all()

    emp_ids = {log.employee_id for log in logs if log.employee_id}
    employees: dict = {}
    if emp_ids:
        res = await db.execute(select(Employee).where(Employee.id.in_(emp_ids)))
        employees = {e.id: e for e in res.scalars().all()}

    events = []
    for log in logs:
        emp = employees.get(log.employee_id)
        events.append({
            "id": str(log.id),
            "employee_id": str(log.employee_id) if log.employee_id else None,
            "employee_name": emp.full_name if emp else None,
            "employee_code": emp.employee_code if emp else None,
            "event_type": log.event_type,
            "event_time": log.event_time.isoformat() if log.event_time else None,
            "confidence": float(log.confidence_score) if log.confidence_score is not None else None,
        })

    return {"events": events, "count": len(events)}
