
import hashlib
import json
from datetime import datetime, timezone

from models import AuditLog


GENESIS_HASH = "0" * 64


def record_audit(actor_id, document_id, action, details=""):
    """Create a hash-linked audit entry. The caller commits the transaction."""
    previous = AuditLog.query.order_by(AuditLog.id.desc()).first()
    previous_hash = previous.entry_hash if previous else GENESIS_HASH

    created_at = datetime.now(timezone.utc)
    payload = {
        "actor_id": actor_id,
        "document_id": document_id,
        "action": action,
        "details": details,
        "previous_hash": previous_hash,
        "created_at": created_at.isoformat(),
    }

    entry_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    entry = AuditLog(
        actor_id=actor_id,
        document_id=document_id,
        action=action,
        details=details,
        previous_hash=previous_hash,
        entry_hash=entry_hash,
        created_at=created_at,
    )

    from extensions import db
    db.session.add(entry)
    return entry


def verify_audit_chain():
    """Return whether stored entries form a valid hash chain."""
    expected_previous = GENESIS_HASH

    entries = AuditLog.query.order_by(AuditLog.id.asc()).all()

    for entry in entries:
        if entry.previous_hash != expected_previous:
            return False

        payload = {
            "actor_id": entry.actor_id,
            "document_id": entry.document_id,
            "action": entry.action,
            "details": entry.details,
            "previous_hash": entry.previous_hash,
            "created_at": entry.created_at.isoformat(),
        }

        calculated_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()

        if calculated_hash != entry.entry_hash:
            return False

        expected_previous = entry.entry_hash

    return True
