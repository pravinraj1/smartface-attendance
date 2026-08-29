from fastapi import APIRouter
from app.api.v1 import auth, departments, employees, attendance, faces, erp, reports, audit

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(departments.router)
api_router.include_router(employees.router)
api_router.include_router(attendance.router)
api_router.include_router(faces.router)
api_router.include_router(erp.router)
api_router.include_router(reports.router)
api_router.include_router(audit.router)
