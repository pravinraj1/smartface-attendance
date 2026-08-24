from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import date, datetime
import json

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.attendance import Attendance
from app.models.employee import Employee
from app.models.erp_config import ERPConfig, ERPsyncLog
from app.services.erp_integration import erp_service

router = APIRouter(prefix="/erp", tags=["ERP Integration"])


@router.get("/config")
async def get_erp_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(ERPConfig).limit(1))
    config = result.scalar_one_or_none()
    if not config:
        return {"configured": False}
    return {
        "configured": True,
        "id": str(config.id),
        "erp_name": config.erp_name,
        "erp_url": config.erp_url,
        "auth_type": config.auth_type,
        "data_format": config.data_format,
        "sync_enabled": config.sync_enabled,
        "sync_interval_minutes": config.sync_interval_minutes,
        "last_sync_at": config.last_sync_at.isoformat() if config.last_sync_at else None,
        "last_sync_status": config.last_sync_status,
        "webhook_enabled": config.webhook_enabled,
        "endpoint_attendance": config.endpoint_attendance,
        "endpoint_employees": config.endpoint_employees,
    }


@router.post("/config")
async def save_erp_config(
    erp_name: str = "Custom ERP",
    erp_url: str = "",
    api_key: str = "",
    auth_type: str = "api_key",
    data_format: str = "xml",
    sync_enabled: bool = True,
    sync_interval_minutes: int = 15,
    endpoint_attendance: str = "",
    endpoint_employees: str = "",
    webhook_url: str = "",
    webhook_secret: str = "",
    webhook_enabled: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(ERPConfig).limit(1))
    config = result.scalar_one_or_none()

    if config:
        config.erp_name = erp_name
        config.erp_url = erp_url
        config.api_key = api_key
        config.auth_type = auth_type
        config.data_format = data_format
        config.sync_enabled = sync_enabled
        config.sync_interval_minutes = sync_interval_minutes
        config.endpoint_attendance = endpoint_attendance
        config.endpoint_employees = endpoint_employees
        config.webhook_url = webhook_url
        config.webhook_secret = webhook_secret
        config.webhook_enabled = webhook_enabled
        config.updated_at = datetime.utcnow()
    else:
        config = ERPConfig(
            erp_name=erp_name,
            erp_url=erp_url,
            api_key=api_key,
            auth_type=auth_type,
            data_format=data_format,
            sync_enabled=sync_enabled,
            sync_interval_minutes=sync_interval_minutes,
            endpoint_attendance=endpoint_attendance,
            endpoint_employees=endpoint_employees,
            webhook_url=webhook_url,
            webhook_secret=webhook_secret,
            webhook_enabled=webhook_enabled,
        )
        db.add(config)

    await db.commit()
    return {"success": True, "message": "ERP configuration saved"}


@router.get("/export/attendance")
async def export_attendance_xml(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    format: str = Query("xml", regex="^(xml|json)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Attendance)
    if start_date:
        query = query.where(Attendance.attendance_date >= start_date)
    if end_date:
        query = query.where(Attendance.attendance_date <= end_date)
    query = query.order_by(Attendance.attendance_date.desc())

    result = await db.execute(query)
    records = result.scalars().all()

    emp_ids = list(set(r.employee_id for r in records if r.employee_id))
    emp_result = await db.execute(select(Employee).where(Employee.id.in_(emp_ids)) if emp_ids else select(Employee).limit(0))
    employees = {str(e.id): {"code": e.employee_code, "name": e.full_name} for e in emp_result.scalars().all()}

    if format == "json":
        data = erp_service.attendance_to_json(records, employees)
        return Response(
            content=json.dumps(data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=attendance_export.json"},
        )
    else:
        xml_content = erp_service.attendance_to_xml(records, employees)
        return Response(
            content=xml_content,
            media_type="application/xml",
            headers={"Content-Disposition": "attachment; filename=attendance_export.xml"},
        )


@router.get("/export/employees")
async def export_employees_xml(
    format: str = Query("xml", regex="^(xml|json)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Employee))
    employees = result.scalars().all()

    if format == "json":
        data = [
            {
                "id": str(e.id),
                "employee_code": e.employee_code,
                "full_name": e.full_name,
                "email": e.email,
                "department_id": str(e.department_id) if e.department_id else None,
                "designation": e.designation,
                "employment_status": e.employment_status,
                "date_of_joining": str(e.date_of_joining) if e.date_of_joining else None,
                "face_enrolled": e.face_enrolled,
            }
            for e in employees
        ]
        return Response(
            content=json.dumps(data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=employees_export.json"},
        )
    else:
        xml_content = erp_service.employee_to_xml(employees)
        return Response(
            content=xml_content,
            media_type="application/xml",
            headers={"Content-Disposition": "attachment; filename=employees_export.xml"},
        )


@router.post("/push/attendance")
async def push_attendance_to_erp(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(ERPConfig).limit(1))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=400, detail="ERP not configured. Save config first.")
    if not config.endpoint_attendance:
        raise HTTPException(status_code=400, detail="Attendance endpoint not set in ERP config.")

    query = select(Attendance)
    if start_date:
        query = query.where(Attendance.attendance_date >= start_date)
    if end_date:
        query = query.where(Attendance.attendance_date <= end_date)
    query = query.order_by(Attendance.attendance_date.desc())
    att_result = await db.execute(query)
    records = att_result.scalars().all()

    emp_ids = list(set(r.employee_id for r in records if r.employee_id))
    emp_result = await db.execute(select(Employee).where(Employee.id.in_(emp_ids)) if emp_ids else select(Employee).limit(0))
    employees = {str(e.id): {"code": e.employee_code, "name": e.full_name} for e in emp_result.scalars().all()}

    if config.data_format == "json":
        payload = json.dumps({"attendance": erp_service.attendance_to_json(records, employees)}, indent=2)
    else:
        payload = erp_service.attendance_to_xml(records, employees)

    push_result = await erp_service.push_to_erp(
        config.endpoint_attendance,
        config.api_key or "",
        payload,
        config.data_format,
    )

    sync_log = ERPsyncLog(
        erp_config_id=config.id,
        sync_type="attendance_push",
        direction="push",
        status="success" if push_result["success"] else "failed",
        records_count=len(records),
        error_message=None if push_result["success"] else push_result.get("response", ""),
        request_payload=payload[:2000],
        response_payload=push_result.get("response", "")[:2000],
        completed_at=datetime.utcnow(),
    )
    db.add(sync_log)

    config.last_sync_at = datetime.utcnow()
    config.last_sync_status = "success" if push_result["success"] else "failed"
    config.last_sync_message = push_result.get("response", "")[:500]
    await db.commit()

    return {
        "success": push_result["success"],
        "records_pushed": len(records),
        "status_code": push_result.get("status_code"),
        "response": push_result.get("response", "")[:500],
    }


@router.post("/webhook/test")
async def test_webhook(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(ERPConfig).limit(1))
    config = result.scalar_one_or_none()
    if not config or not config.webhook_url:
        raise HTTPException(status_code=400, detail="Webhook not configured")

    test_data = {"test": True, "message": "SmartFace webhook test", "timestamp": datetime.utcnow().isoformat()}
    webhook_result = await erp_service.send_webhook(config.webhook_url, config.webhook_secret or "", "test", test_data)

    return {"success": webhook_result["success"], "status_code": webhook_result.get("status_code")}


@router.get("/sync-logs")
async def get_sync_logs(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ERPsyncLog).order_by(ERPsyncLog.started_at.desc()).limit(limit)
    )
    logs = result.scalars().all()
    return [
        {
            "id": str(log.id),
            "sync_type": log.sync_type,
            "direction": log.direction,
            "status": log.status,
            "records_count": log.records_count,
            "error_message": log.error_message,
            "started_at": log.started_at.isoformat() if log.started_at else None,
            "completed_at": log.completed_at.isoformat() if log.completed_at else None,
        }
        for log in logs
    ]


@router.get("/public/attendance")
async def public_attendance_export(
    api_key: str = Query(...),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    format: str = Query("xml", regex="^(xml|json)$"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ERPConfig).limit(1))
    config = result.scalar_one_or_none()
    if not config or config.api_key != api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    query = select(Attendance)
    if start_date:
        query = query.where(Attendance.attendance_date >= start_date)
    if end_date:
        query = query.where(Attendance.attendance_date <= end_date)
    query = query.order_by(Attendance.attendance_date.desc())

    att_result = await db.execute(query)
    records = att_result.scalars().all()

    emp_ids = list(set(r.employee_id for r in records if r.employee_id))
    emp_result = await db.execute(select(Employee).where(Employee.id.in_(emp_ids)) if emp_ids else select(Employee).limit(0))
    employees = {str(e.id): {"code": e.employee_code, "name": e.full_name} for e in emp_result.scalars().all()}

    if format == "json":
        data = erp_service.attendance_to_json(records, employees)
        return Response(content=json.dumps(data, indent=2), media_type="application/json")
    else:
        xml_content = erp_service.attendance_to_xml(records, employees)
        return Response(content=xml_content, media_type="application/xml")


@router.get("/public/employees")
async def public_employee_export(
    api_key: str = Query(...),
    format: str = Query("xml", regex="^(xml|json)$"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ERPConfig).limit(1))
    config = result.scalar_one_or_none()
    if not config or config.api_key != api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    emp_result = await db.execute(select(Employee))
    employees = emp_result.scalars().all()

    if format == "json":
        data = [
            {
                "id": str(e.id),
                "employee_code": e.employee_code,
                "full_name": e.full_name,
                "email": e.email,
                "department_id": str(e.department_id) if e.department_id else None,
                "designation": e.designation,
                "employment_status": e.employment_status,
            }
            for e in employees
        ]
        return Response(content=json.dumps(data, indent=2), media_type="application/json")
    else:
        xml_content = erp_service.employee_to_xml(employees)
        return Response(content=xml_content, media_type="application/xml")
