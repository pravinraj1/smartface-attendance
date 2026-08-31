import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.models.user import User
from app.models.employee import Employee
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeResponse,
    EmployeeListResponse,
)
from app.services.audit import record_audit
from pydantic import BaseModel, conlist

router = APIRouter(prefix="/employees", tags=["Employees"])


class BulkImportRequest(BaseModel):
    employees: conlist(EmployeeCreate, min_length=1, max_length=500)


@router.post("/bulk", summary="Bulk import employees")
async def bulk_create_employees(
    body: BulkImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Batch-create up to 500 employees at once. Skips any that collide on
    employee_code or mobile_number; returns per-row results and a summary."""
    created = []
    skipped = []
    errors = []

    codes = [e.employee_code for e in body.employees]
    existing_codes = set()
    for chunk in range(0, len(codes), 100):
        res = await db.execute(
            select(Employee.employee_code).where(Employee.employee_code.in_(codes[chunk:chunk + 100]))
        )
        existing_codes.update(res.scalars().all())

    mobiles = [e.mobile_number for e in body.employees if e.mobile_number]
    existing_mobiles = set()
    for chunk in range(0, len(mobiles), 100):
        res = await db.execute(
            select(Employee.mobile_number).where(Employee.mobile_number.in_(mobiles[chunk:chunk + 100]))
        )
        existing_mobiles.update(res.scalars().all())

    seen_codes = set()
    seen_mobiles = set()
    for emp_data in body.employees:
        try:
            if emp_data.employee_code in existing_codes or emp_data.employee_code in seen_codes:
                skipped.append({"employee_code": emp_data.employee_code, "reason": "employee_code already exists"})
                continue
            if emp_data.mobile_number:
                if emp_data.mobile_number in existing_mobiles or emp_data.mobile_number in seen_mobiles:
                    skipped.append({"employee_code": emp_data.employee_code, "reason": "mobile_number already registered"})
                    continue
            employee = Employee(**emp_data.model_dump())
            db.add(employee)
            seen_codes.add(emp_data.employee_code)
            if emp_data.mobile_number:
                seen_mobiles.add(emp_data.mobile_number)
            created.append(employee.employee_code)
        except Exception as exc:  # noqa: BLE001
            errors.append({"employee_code": getattr(emp_data, "employee_code", "?"), "error": str(exc)})

        if (len(created) + len(skipped) + len(errors)) % 200 == 0:
            await db.flush()

    await db.commit()

    await record_audit(
        db,
        user_id=current_user.id,
        action="BULK_CREATE",
        entity_name="employee",
        new_value={"created": len(created), "skipped": len(skipped), "errors": len(errors)},
    )
    await db.commit()

    return {
        "imported": len(created),
        "skipped": skipped,
        "errors": errors,
        "total_received": len(body.employees),
    }


@router.get("", response_model=EmployeeListResponse)
async def get_employees(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=500),
    search: Optional[str] = None,
    department_id: Optional[str] = None,
    employment_status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Employee)
    count_query = select(func.count(Employee.id))
    
    if search:
        search_filter = Employee.full_name.ilike(f"%{search}%") | Employee.employee_code.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    if department_id:
        try:
            dept_uuid = uuid.UUID(department_id)
            query = query.where(Employee.department_id == dept_uuid)
            count_query = count_query.where(Employee.department_id == dept_uuid)
        except ValueError:
            pass
    
    if employment_status:
        query = query.where(Employee.employment_status == employment_status)
        count_query = count_query.where(Employee.employment_status == employment_status)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    employees = result.scalars().all()
    
    return EmployeeListResponse(
        employees=employees,
        total=total,
        page=(skip // limit) + 1,
        page_size=limit,
    )


@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Employee).where(Employee.id == employee_id)
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    employee_data: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    existing = await db.execute(
        select(Employee).where(Employee.employee_code == employee_data.employee_code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee code already exists",
        )
    
    if employee_data.mobile_number:
        existing_mobile = await db.execute(
            select(Employee).where(Employee.mobile_number == employee_data.mobile_number)
        )
        if existing_mobile.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mobile number already registered",
            )
    
    employee = Employee(**employee_data.model_dump())
    db.add(employee)
    await db.commit()
    await db.refresh(employee)
    await record_audit(
        db,
        user_id=current_user.id,
        action="CREATE",
        entity_name="employee",
        entity_id=employee.id,
        new_value={"employee_code": employee.employee_code, "full_name": employee.full_name},
    )
    await db.commit()
    return employee


@router.put("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: uuid.UUID,
    employee_data: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(Employee).where(Employee.id == employee_id)
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    update_data = employee_data.model_dump(exclude_unset=True)
    old_values = {
        "employee_code": employee.employee_code,
        "full_name": employee.full_name,
        "department_id": employee.department_id,
        "employment_status": employee.employment_status,
        "monthly_salary": employee.monthly_salary,
    }
    for key, value in update_data.items():
        setattr(employee, key, value)
    
    await db.commit()
    await db.refresh(employee)
    await record_audit(
        db,
        user_id=current_user.id,
        action="UPDATE",
        entity_name="employee",
        entity_id=employee.id,
        old_value=old_values,
        new_value={
            "employee_code": employee.employee_code,
            "full_name": employee.full_name,
            "department_id": employee.department_id,
            "employment_status": employee.employment_status,
            **update_data,
        },
    )
    await db.commit()
    return employee


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    employee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(Employee).where(Employee.id == employee_id)
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    await record_audit(
        db,
        user_id=current_user.id,
        action="DELETE",
        entity_name="employee",
        entity_id=employee.id,
        old_value={"employee_code": employee.employee_code, "full_name": employee.full_name},
    )
    await db.delete(employee)
    await db.commit()
