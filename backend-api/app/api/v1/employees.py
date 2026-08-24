from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.employee import Employee
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeResponse,
    EmployeeListResponse,
)

router = APIRouter(prefix="/employees", tags=["Employees"])


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
        query = query.where(Employee.department_id == department_id)
        count_query = count_query.where(Employee.department_id == department_id)
    
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
    employee_id: str,
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
    current_user: User = Depends(get_current_user),
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
    return employee


@router.put("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: str,
    employee_data: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Employee).where(Employee.id == employee_id)
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    update_data = employee_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(employee, key, value)
    
    await db.commit()
    await db.refresh(employee)
    return employee


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    employee_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Employee).where(Employee.id == employee_id)
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    await db.delete(employee)
    await db.commit()
