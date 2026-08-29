import uuid
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.audit_log import AuditLog


def _serializable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, uuid.UUID):
        return str(value)
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except TypeError:
            return str(value)
    return str(value)


def _clean_dict(mapping: dict) -> dict:
    return {k: _serializable(v) for k, v in (mapping or {}).items() if not k.startswith("_")}


async def record_audit(
    db: AsyncSession,
    user_id: Optional[uuid.UUID],
    action: str,
    entity_name: str,
    entity_id: Optional[uuid.UUID] = None,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
) -> None:
    """Persist an audit-log entry. Never raises; failures are swallowed to keep business flows intact."""
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_name=entity_name,
            entity_id=entity_id,
            old_value=_clean_dict(old_value) if old_value else None,
            new_value=_clean_dict(new_value) if new_value else None,
        )
        db.add(entry)
        await db.flush()
    except Exception:
        await db.rollback()
