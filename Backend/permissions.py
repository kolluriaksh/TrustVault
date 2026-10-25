
from models import Document, DocumentShare


def get_document_permission(user_id, document_id):
    """
    Return 'owner', 'read', or None.
    Only an owner or an explicitly shared user is authorized.
    """
    document = db_get_document(document_id)

    if document is None:
        return None

    if document.owner_id == user_id:
        return "owner"

    share = DocumentShare.query.filter_by(
        document_id=document_id,
        user_id=user_id,
    ).first()

    if share and share.permission == "read":
        return "read"

    return None


def db_get_document(document_id):
    from extensions import db
    return db.session.get(Document, document_id)


def can_read_document(user_id, document_id):
    return get_document_permission(user_id, document_id) in (
        "owner", "read"
    )


def can_manage_document(user_id, document_id):
    return get_document_permission(user_id, document_id) == "owner"
