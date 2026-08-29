import io
import csv
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from datetime import date

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.attendance import Attendance
from app.models.employee import Employee
from app.models.department import Department

router = APIRouter(prefix="/reports", tags=["Reports"])


def _date_filter(query, start_date, end_date):
    if start_date:
        query = query.where(Attendance.attendance_date >= start_date)
    if end_date:
        query = query.where(Attendance.attendance_date <= end_date)
    return query


def _csv_response(rows: List[dict], filename: str) -> Response:
    if not rows:
        rows = [{"message": "No data"}]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    payload = buffer.getvalue()
    # BOM so Excel opens UTF-8 CSVs correctly
    body = "\ufeff".encode("utf-8") + payload.encode("utf-8")
    return Response(
        content=body,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _resolve_employees(db, emp_ids) -> dict:
    ids = list({e for e in emp_ids if e is not None})
    if not ids:
        return {}
    res = await db.execute(select(Employee).where(Employee.id.in_(ids)))
    return {e.id: e for e in res.scalars().all()}


@router.get("/summary")
async def report_summary(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    department_id: Optional[str] = None,
    format: Optional[str] = Query(None, pattern="^(csv|json)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_employees = (await db.execute(select(func.count(Employee.id)))).scalar() or 0

    emp_ids = None
    if department_id:
        emp_result = await db.execute(
            select(Employee.id).where(Employee.department_id == department_id)
        )
        emp_ids = list(emp_result.scalars().all())

    att_query = select(Attendance)
    if emp_ids:
        att_query = att_query.where(Attendance.employee_id.in_(emp_ids))
    att_query = _date_filter(att_query, start_date, end_date)
    att_result = await db.execute(att_query)
    records = att_result.scalars().all()

    total_records = len(records)
    present = sum(1 for r in records if r.check_in is not None)
    late = sum(1 for r in records if (r.late_minutes or 0) > 0)

    unique_dates = {r.attendance_date for r in records}
    total_working_days = len(unique_dates)
    active_emp_days = max(total_employees * total_working_days, 1)
    avg_attendance_rate = present / active_emp_days if active_emp_days else 0.0

    total_absences = max(total_employees * total_working_days - present, 0)

    # Department breakdown
    dept_query = select(Department).where(Department.is_active == True)
    departments = (await db.execute(dept_query)).scalars().all()

    department_summary = []
    for dept in departments:
        dept_emp_ids_res = await db.execute(
            select(Employee.id).where(Employee.department_id == dept.id)
        )
        dept_emp_ids = list(dept_emp_ids_res.scalars().all())
        if not dept_emp_ids:
            continue
        d_query = select(Attendance)
        if emp_ids is not None and department_id is not None:
            d_query = d_query.where(Attendance.employee_id.in_(dept_emp_ids))
        d_query = _date_filter(d_query, start_date, end_date)
        d_records = (await db.execute(d_query)).scalars().all()
        d_present = sum(1 for r in d_records if r.check_in is not None)
        d_late = sum(1 for r in d_records if (r.late_minutes or 0) > 0)
        d_absent = max(len(dept_emp_ids) * total_working_days - d_present, 0)
        department_summary.append({
            "department_id": str(dept.id),
            "department_name": dept.name,
            "present_days": d_present,
            "absent_days": d_absent,
            "late_days": d_late,
            "total_employees": len(dept_emp_ids),
        })

    data = {
        "total_working_days": total_working_days,
        "avg_attendance_rate": round(avg_attendance_rate, 4),
        "total_absences": total_absences,
        "total_records": total_records,
        "total_employees": total_employees,
        "present_days": present,
        "late_days": late,
        "department_summary": department_summary,
    }

    if format == "csv":
        rows = [{
            "department_name": d["department_name"],
            "total_employees": d["total_employees"],
            "present_days": d["present_days"],
            "absent_days": d["absent_days"],
            "late_days": d["late_days"],
        } for d in department_summary]
        rows.append({
            "department_name": "ALL",
            "total_employees": total_employees,
            "present_days": present,
            "absent_days": total_absences,
            "late_days": late,
        })
        return _csv_response(rows, "attendance_summary.csv")

    return data


@router.get("/employee/{employee_id}")
async def report_employee(
    employee_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    format: Optional[str] = Query(None, pattern="^(csv|json)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employee = (await db.execute(select(Employee).where(Employee.id == employee_id))).scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    query = select(Attendance).where(Attendance.employee_id == employee_id)
    query = _date_filter(query, start_date, end_date)
    query = query.order_by(Attendance.attendance_date.asc())
    records = (await db.execute(query)).scalars().all()

    present = sum(1 for r in records if r.check_in is not None)
    late = sum(1 for r in records if (r.late_minutes or 0) > 0)
    total_work_minutes = sum(r.total_work_minutes or 0 for r in records)
    days = len(records)

    records_payload = [
        {
            "date": str(r.attendance_date),
            "check_in": r.check_in.isoformat() if r.check_in else None,
            "check_out": r.check_out.isoformat() if r.check_out else None,
            "work_minutes": r.total_work_minutes or 0,
            "status": r.attendance_status or "",
            "late_minutes": r.late_minutes or 0,
        }
        for r in records
    ]

    if format == "csv":
        rows = [{
            "employee_code": employee.employee_code,
            "employee_name": employee.full_name,
            **rc,
        } for rc in records_payload]
        return _csv_response(rows, f"employee_report_{employee.employee_code}.csv")

    return {
        "employee_id": employee_id,
        "employee_name": employee.full_name,
        "employee_code": employee.employee_code,
        "total_days": days,
        "present_days": present,
        "absent_days": max(days - present, 0),
        "late_days": late,
        "total_work_minutes": total_work_minutes,
        "attendance_rate": round(present / days, 4) if days else 0.0,
        "records": records_payload,
    }


@router.get("/department/{department_id}")
async def report_department(
    department_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    format: Optional[str] = Query(None, pattern="^(csv|json)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    department = (await db.execute(select(Department).where(Department.id == department_id))).scalar_one_or_none()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    emp_ids_res = await db.execute(select(Employee.id).where(Employee.department_id == department_id))
    emp_ids = list(emp_ids_res.scalars().all())

    if not emp_ids:
        empty = {
            "department_id": department_id,
            "department_name": department.name,
            "total_employees": 0,
            "present_days": 0,
            "absent_days": 0,
            "late_days": 0,
            "attendance_rate": 0.0,
            "records": [],
        }
        if format == "csv":
            return _csv_response([], f"department_report_{department.name}.csv")
        return empty

    query = select(Attendance)
    query = query.where(Attendance.employee_id.in_(emp_ids))
    query = _date_filter(query, start_date, end_date)
    query = query.order_by(Attendance.attendance_date.asc())
    records = (await db.execute(query)).scalars().all()

    present = sum(1 for r in records if r.check_in is not None)
    late = sum(1 for r in records if (r.late_minutes or 0) > 0)
    days = len({r.attendance_date for r in records})
    total_slots = max(len(emp_ids) * days, 1)

    employees = await _resolve_employees(db, emp_ids)

    records_payload = [
        {
            "employee_id": str(r.employee_id),
            "employee_code": employees.get(r.employee_id).employee_code if employees.get(r.employee_id) else None,
            "employee_name": employees.get(r.employee_id).full_name if employees.get(r.employee_id) else None,
            "date": str(r.attendance_date),
            "check_in": r.check_in.isoformat() if r.check_in else None,
            "check_out": r.check_out.isoformat() if r.check_out else None,
            "work_minutes": r.total_work_minutes or 0,
            "status": r.attendance_status or "",
        }
        for r in records
    ]

    if format == "csv":
        rows = [{k: v for k, v in rc.items() if k != "employee_id"} for rc in records_payload]
        return _csv_response(rows, f"department_report_{department.name}.csv")

    return {
        "department_id": department_id,
        "department_name": department.name,
        "total_employees": len(emp_ids),
        "present_days": present,
        "absent_days": max(total_slots - present, 0),
        "late_days": late,
        "attendance_rate": round(present / total_slots, 4) if total_slots else 0.0,
        "records": records_payload,
    }
