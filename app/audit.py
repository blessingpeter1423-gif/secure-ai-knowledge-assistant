from sqlalchemy.orm import Session

from app.models import AuditLog, UsageEvent


def create_audit_log(
    db: Session,
    tenant_id: int,
    user_id: int | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    status: str = "success"
):
    log = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        status=status
    )

    db.add(log)

    return log


def record_usage(
    db: Session,
    tenant_id: int,
    user_id: int | None,
    event_type: str,
    quantity: int = 1
):
    event = UsageEvent(
        tenant_id=tenant_id,
        user_id=user_id,
        event_type=event_type,
        quantity=quantity
    )

    db.add(event)

    return event