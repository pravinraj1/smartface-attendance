import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import require_admin
from app.models.user import User
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/audit-logs", tags=["Audit"])


@router.get("")
async def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    entity_name: Optional[str] = None,
    action: Optional[str] = None,
    entity_id: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    query = select(AuditLog)

    filters = []
    if entity_name:
        filters.append(AuditLog.entity_name == entity_name)
    if action:
        filters.append(AuditLog.action == action)
    if entity_id:
        try:
            filters.append(AuditLog.entity_id == uuid.UUID(entity_id))
        except ValueError:
            pass
    if user_id:
        try:
            filters.append(AuditLog.user_id == uuid.UUID(user_id))
        except ValueError:
            pass
    if start_date:
        filters.append(AuditLog.created_at >= start_date)
    if end_date:
        filters.append(AuditLog.created_at <= end_date)

    if filters:
        from sqlalchemy import and_
        query = query.where(and_(*filters))

    total = (await db.execute(
        select(func.count(AuditLog.id))
    )).scalar() or 0

    query = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
    logs = (await db.execute(query)).scalars().all()

    user_ids = list({log.user_id for log in logs if log.user_id})
    users = {}
    if user_ids:
        from app.models.user import User as UserModel
        res = await db.execute(select(UserModel).where(UserModel.id.in_(user_ids)))
        users = {u.id: u.email for u in res.scalars().all()}

    return {
        "total": total,
        "logs": [
            {
                "id": str(log.id),
                "user_id": str(log.user_id) if log.user_id else None,
                "user_email": users.get(log.user_id),
                "action": log.action,
                "entity_name": log.entity_name,
                "entity_id": str(log.entity_id) if log.entity_id else None,
                "old_value": log.old_value,
                "new_value": log.new_value,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
    }
