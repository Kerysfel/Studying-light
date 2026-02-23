"""Audit log service helpers."""

import uuid

from sqlalchemy.orm import Session

from studying_light.db.models.audit_log import AuditLog


def record_audit_event(
    session: Session,
    *,
    actor_user_id: uuid.UUID,
    action: str,
    target_user_id: uuid.UUID | None = None,
    payload_json: dict | None = None,
) -> AuditLog:
    """Persist and return an audit log record."""
    entry = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        target_user_id=target_user_id,
        payload_json=payload_json,
    )
    session.add(entry)
    return entry
