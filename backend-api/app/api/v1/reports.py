import io
import csv
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.attendance import Attendance
from app.models.employee import Employee
from app.models.department import Department
from app.services.report_pdf import build_table_pdf, minutes_to_hours

router = APIRouter(prefix="/reports", tags=["Reports"])

try:
    _TZ = ZoneInfo("Asia/Kolkata")
except Exception:  # pragma: no cover
    from datetime import timezone
    _TZ = timezone(timedelta(hours=5, minutes=30))


def _today_ist() -> date:
    from datetime import datetime
    return datetime.now(_TZ).date()


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


def _pdf_response(content: bytes, filename: str) -> Response:
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _resolve_period(period: Optional[str], start_date: Optional[date], end_date: Optional[date]):
    """Resolve a date range. A named `period` (day/week/month) takes
    precedence; otherwise falls back to the given start/end dates."""
    start = start_date
    end = end_date
    today = _today_ist()

    if period:
        if period == "day":
            start = end = today
        elif period == "week":
            # Monday-based week containing today.
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
        elif period == "month":
            start = today.replace(day=1)
            next_month = (start + timedelta(days=32)).replace(day=1)
            end = next_month - timedelta(days=1)
        else:
            raise HTTPException(status_code=400, detail="period must be one of: day, week, month")
        if end < start:
            end = start

    return start, end


def _period_label(period: Optional[str], start_date: Optional[date], end_date: Optional[date]) -> str:
    if period == "day":
        return f"Daily Report - {_today_ist()}"
    if period == "week":
        s = start_date or _today_ist()
        e = end_date or s
        return f"Weekly Report - {s} to {e}"
    if period == "month":
        s = start_date or _today_ist()
        e = end_date or s
        return f"Monthly Report - {s} to {e}"
    if not start_date and not end_date:
        return "Attendance Report - All Time"
    return f"Attendance Report - {start_date or '...'} to {end_date or '...'}"



async def _resolve_employees(db, emp_ids) -> dict:
    ids = list({e for e in emp_ids if e is not None})
    if not ids:
        return {}
    res = await db.execute(select(Employee).where(Employee.id.in_(ids)))
    return {e.id: e for e in res.scalars().all()}


@router.get("/summary")
async def report_summary(
    period: Optional[str] = Query(None, pattern="^(day|week|month)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    department_id: Optional[str] = None,
    employee_id: Optional[str] = None,
    format: Optional[str] = Query(None, pattern="^(csv|pdf|json)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    start_date, end_date = _resolve_period(period, start_date, end_date)

    total_employees = (await db.execute(select(func.count(Employee.id)))).scalar() or 0

    emp_ids = list({e for e in [employee_id] if e}) if employee_id else None
    if not emp_ids and department_id:
        emp_result = await db.execute(
            select(Employee.id).where(Employee.department_id == department_id)
        )
        emp_ids = list(emp_result.scalars().all())

    if employee_id:
        emp_ids = [employee_id]

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

    if emp_ids is not None:
        eff_total_employees = len(set(emp_ids))
    else:
        eff_total_employees = total_employees
    active_emp_days = max(eff_total_employees * total_working_days, 1)
    avg_attendance_rate = present / active_emp_days if active_emp_days else 0.0

    total_absences = max(eff_total_employees * total_working_days - present, 0)

    # Department breakdown
    dept_query = select(Department).where(Department.is_active == True)
    departments = (await db.execute(dept_query)).scalars().all()

    department_summary = []
    for dept in departments:
        dept_emp_ids_res = await db.execute(
            select(Employee.id).where(Employee.department_id == dept.id)
        )
        dept_emp_ids = list(dept_emp_ids_res.scalars().all())
        if emp_ids is not None:
            dept_emp_ids = [e for e in dept_emp_ids if e in set(emp_ids)]
        if not dept_emp_ids:
            continue
        d_query = select(Attendance).where(Attendance.employee_id.in_(dept_emp_ids))
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
        "total_employees": eff_total_employees,
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
            "total_employees": eff_total_employees,
            "present_days": present,
            "absent_days": total_absences,
            "late_days": late,
        })
        return _csv_response(rows, "attendance_summary.csv")

    if format == "pdf":
        summary_block = [
            ("Period", _period_label(period, start_date, end_date)),
            ("Employees", str(eff_total_employees)),
            ("Working Days", str(total_working_days)),
            ("Present", str(present)),
            ("Absent", str(total_absences)),
            ("Late", str(late)),
            ("Attendance Rate", f"{round(avg_attendance_rate * 100, 1)}%"),
        ]
        cols = ["Department", "Employees", "Present", "Absent", "Late"]
        pdf_rows = [
            [d["department_name"], str(d["total_employees"]), str(d["present_days"]),
             str(d["absent_days"]), str(d["late_days"])]
            for d in department_summary
        ]
        pdf_rows.append(["ALL", str(eff_total_employees), str(present), str(total_absences), str(late)])
        pdf = build_table_pdf(
            _period_label(period, start_date, end_date) or "Attendance Summary",
            "Department-wise attendance summary",
            cols, pdf_rows,
            summary_block=summary_block,
        )
        return _pdf_response(pdf, "attendance_summary.pdf")

    return data


@router.get("/employee/{employee_id}")
async def report_employee(
    employee_id: str,
    period: Optional[str] = Query(None, pattern="^(day|week|month)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    format: Optional[str] = Query(None, pattern="^(csv|pdf|json)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employee = (await db.execute(select(Employee).where(Employee.id == employee_id))).scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    start_date, end_date = _resolve_period(period, start_date, end_date)

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

    if format == "pdf":
        summary_block = [
            ("Employee", f"{employee.full_name} ({employee.employee_code})"),
            ("Period", _period_label(period, start_date, end_date)),
            ("Working Days", str(days)),
            ("Present", str(present)),
            ("Absent", str(max(days - present, 0))),
            ("Late", str(late)),
            ("Total Hours", minutes_to_hours(total_work_minutes)),
            ("Attendance Rate", f"{round(present / days * 100, 1) if days else 0}%"),
        ]
        def _fmt_time(iso: Optional[str]) -> str:
            if not iso:
                return "-"
            t = iso[11:16]
            return t
        cols = ["Date", "Check In", "Check Out", "Hours", "Status", "Late (min)"]
        pdf_rows = [
            [rc["date"], _fmt_time(rc["check_in"]), _fmt_time(rc["check_out"]),
             minutes_to_hours(rc["work_minutes"]), rc["status"] or "-", str(rc["late_minutes"] or 0)]
            for rc in records_payload
        ]
        if not pdf_rows:
            pdf_rows = [["No attendance records in this period", "-", "-", "-", "-", "-"]]
        pdf = build_table_pdf(
            _period_label(period, start_date, end_date) or "Employee Report",
            f"{employee.full_name} ({employee.employee_code})",
            cols, pdf_rows,
            summary_block=summary_block,
        )
        return _pdf_response(pdf, f"employee_report_{employee.employee_code}.pdf")

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
    period: Optional[str] = Query(None, pattern="^(day|week|month)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    format: Optional[str] = Query(None, pattern="^(csv|pdf|json)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    department = (await db.execute(select(Department).where(Department.id == department_id))).scalar_one_or_none()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    start_date, end_date = _resolve_period(period, start_date, end_date)

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
        if format == "pdf":
            pdf = build_table_pdf(
                _period_label(period, start_date, end_date) or "Department Report",
                department.name,
                ["Employee", "Date", "Check In", "Check Out", "Hours", "Status"],
                [["No employees in this department", "-", "-", "-", "-", "-"]],
            )
            return _pdf_response(pdf, f"department_report_{department.name}.pdf")
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

    if format == "pdf":
        def _fmt_time(iso: Optional[str]) -> str:
            if not iso:
                return "-"
            return iso[11:16]
        summary_block = [
            ("Department", department.name),
            ("Period", _period_label(period, start_date, end_date)),
            ("Employees", str(len(emp_ids))),
            ("Present", str(present)),
            ("Absent", str(max(total_slots - present, 0))),
            ("Late", str(late)),
            ("Attendance Rate", f"{round(present / total_slots * 100, 1) if total_slots else 0}%"),
        ]
        cols = ["Employee", "Code", "Date", "In", "Out", "Hours", "Status"]
        pdf_rows = [
            [rc["employee_name"] or "-", rc["employee_code"] or "-", rc["date"],
             _fmt_time(rc["check_in"]), _fmt_time(rc["check_out"]),
             minutes_to_hours(rc["work_minutes"]), rc["status"] or "-"]
            for rc in records_payload
        ]
        if not pdf_rows:
            pdf_rows = [["No attendance records in this period", "-", "-", "-", "-", "-", "-"]]
        pdf = build_table_pdf(
            _period_label(period, start_date, end_date) or "Department Report",
            department.name,
            cols, pdf_rows,
            summary_block=summary_block,
            landscape_page=True,
        )
        return _pdf_response(pdf, f"department_report_{department.name}.pdf")

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
