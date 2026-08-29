from typing import List, Optional
from datetime import date, datetime
from xml.etree.ElementTree import Element, SubElement, tostring, ElementTree
import xml.dom.minidom as minidom
import httpx
import json

from app.models.attendance import Attendance
from app.models.attendance_log import AttendanceLog
from app.models.employee import Employee


class ERPIntegrationService:
    def __init__(self):
        self._initialized = False

    def initialize(self):
        if self._initialized:
            return
        self._initialized = True
        print("ERP Integration service initialized")

    def attendance_to_xml(self, records: List[Attendance], employees: dict) -> str:
        root = Element("AttendanceExport")
        root.set("exportDate", datetime.utcnow().isoformat())
        root.set("totalRecords", str(len(records)))

        for record in records:
            emp = employees.get(record.employee_id)
            att = SubElement(root, "AttendanceRecord")
            att.set("id", str(record.id))

            emp_elem = SubElement(att, "Employee")
            emp_elem.set("id", str(record.employee_id))
            emp_elem.set("code", emp.get("code", "") if emp else "")
            emp_elem.set("name", emp.get("name", "") if emp else "")

            SubElement(att, "Date").text = str(record.attendance_date)
            SubElement(att, "CheckIn").text = record.check_in.isoformat() if record.check_in else ""
            SubElement(att, "CheckOut").text = record.check_out.isoformat() if record.check_out else ""
            SubElement(att, "WorkMinutes").text = str(record.total_work_minutes or 0)
            SubElement(att, "Status").text = record.attendance_status or ""

        rough = tostring(root, encoding="unicode")
        reparsed = minidom.parseString(rough)
        return reparsed.toprettyxml(indent="  ", encoding=None)

    def employee_to_xml(self, employees: List[Employee]) -> str:
        root = Element("EmployeeExport")
        root.set("exportDate", datetime.utcnow().isoformat())
        root.set("totalRecords", str(len(employees)))

        for emp in employees:
            emp_elem = SubElement(root, "Employee")
            emp_elem.set("id", str(emp.id))
            SubElement(emp_elem, "EmployeeCode").text = emp.employee_code or ""
            SubElement(emp_elem, "FullName").text = emp.full_name or ""
            SubElement(emp_elem, "MobileNumber").text = emp.mobile_number or ""
            SubElement(emp_elem, "DepartmentId").text = str(emp.department_id) if emp.department_id else ""
            SubElement(emp_elem, "EmploymentStatus").text = emp.employment_status or ""
            SubElement(emp_elem, "DateOfJoining").text = str(emp.joining_date) if emp.joining_date else ""
            SubElement(emp_elem, "FaceEnrolled").text = str(emp.face_enrolled or False)

        rough = tostring(root, encoding="unicode")
        reparsed = minidom.parseString(rough)
        return reparsed.toprettyxml(indent="  ", encoding=None)

    def attendance_to_json(self, records: List[Attendance], employees: dict) -> list:
        result = []
        for record in records:
            emp = employees.get(record.employee_id)
            result.append({
                "employee_id": str(record.employee_id),
                "employee_code": emp.get("code", "") if emp else "",
                "employee_name": emp.get("name", "") if emp else "",
                "date": str(record.attendance_date),
                "check_in": record.check_in.isoformat() if record.check_in else None,
                "check_out": record.check_out.isoformat() if record.check_out else None,
                "work_minutes": record.total_work_minutes or 0,
                "status": record.attendance_status or "",
            })
        return result

    async def push_to_erp(self, erp_url: str, api_key: str, payload: str, data_format: str = "xml") -> dict:
        try:
            headers = {"Content-Type": f"application/{data_format}"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    erp_url,
                    content=payload,
                    headers=headers,
                )
                return {
                    "success": response.status_code < 400,
                    "status_code": response.status_code,
                    "response": response.text[:1000],
                }
        except Exception as e:
            return {
                "success": False,
                "status_code": 0,
                "response": str(e),
            }

    async def send_webhook(self, webhook_url: str, webhook_secret: str, event: str, data: dict) -> dict:
        try:
            payload = json.dumps({"event": event, "data": data, "timestamp": datetime.utcnow().isoformat()})
            headers = {"Content-Type": "application/json"}
            if webhook_secret:
                headers["X-Webhook-Secret"] = webhook_secret

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(webhook_url, content=payload, headers=headers)
                return {"success": response.status_code < 400, "status_code": response.status_code}
        except Exception as e:
            return {"success": False, "status_code": 0, "error": str(e)}


erp_service = ERPIntegrationService()
