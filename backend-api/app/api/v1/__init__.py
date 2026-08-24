from fastapi import APIRouter
from app.api.v1 import auth, departments, employees, attendance, faces, erp

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(departments.router)
api_router.include_router(employees.router)
api_router.include_router(attendance.router)
api_router.include_router(faces.router)
api_router.include_router(erp.router)
