
import os
import uuid
from pathlib import Path

from flask import Blueprint, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from extensions import db
from models import Document, DocumentShare, User
from auth import get_current_user, login_required
from permissions import can_read_document, can_manage_document
from audit import record_audit

documents_bp = Blueprint("documents", __name__, url_prefix="/api/documents")


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", str(BASE_DIR / "uploads")))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 16 * 1024 * 1024  # 16 MB
ALLOWED_EXTENSIONS = {
    "pdf", "doc", "docx", "txt", "csv",
    "png", "jpg", "jpeg", "xlsx", "pptx"
}


def audit_and_commit(user_id, document_id, action, details=""):
    record_audit(user_id, document_id, action, details)
    db.session.commit()


def document_json(document, permission):
    return {
        "id": document.id,
        "name": document.original_name,
        "size": document.size_bytes,
        "content_type": document.content_type,
        "owner_id": document.owner_id,
        "permission": permission,
        "created_at": document.created_at.isoformat()
        if document.created_at else None,
    }


@documents_bp.get("")
@login_required
def list_documents():
    user = get_current_user()

    owned = Document.query.filter_by(owner_id=user.id).all()
    shared_records = DocumentShare.query.filter_by(
        user_id=user.id, permission="read"
    ).all()

    results = {}
    for doc in owned:
        results[doc.id] = document_json(doc, "owner")

    for share in shared_records:
        doc = db.session.get(Document, share.document_id)
        if doc:
            results[doc.id] = document_json(doc, "read")

    return jsonify({"documents": list(results.values())})


@documents_bp.post("")
@login_required
def upload_document():
    user = get_current_user()

    if "file" not in request.files:
        return jsonify({"error": "Choose a file to upload."}), 400

    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"error": "Choose a file to upload."}), 400

    safe_name = secure_filename(file.filename)
    if not safe_name or "." not in safe_name:
        return jsonify({"error": "Invalid filename."}), 400

    extension = safe_name.rsplit(".", 1)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        return jsonify({"error": "This file type is not allowed."}), 400

    file.stream.seek(0, os.SEEK_END)
    size = file.stream.tell()
    file.stream.seek(0)

    if size > MAX_FILE_SIZE:
        return jsonify({"error": "Maximum upload size is 16 MB."}), 413

    stored_name = f"{uuid.uuid4().hex}.{extension}"
    destination = UPLOAD_DIR / stored_name

    try:
        file.save(destination)

        doc = Document(
            owner_id=user.id,
            original_name=safe_name,
            stored_name=stored_name,
            content_type=file.mimetype or "application/octet-stream",
            size_bytes=size,
        )
        db.session.add(doc)
        db.session.flush()

        record_audit(
            user.id, doc.id, "document_uploaded",
            f"Uploaded {safe_name}"
        )
        db.session.commit()

        return jsonify({
            "message": "Document uploaded successfully.",
            "document": document_json(doc, "owner"),
        }), 201

    except Exception:
        db.session.rollback()
        if destination.exists():
            destination.unlink()
        raise


@documents_bp.get("/<int:document_id>/download")
@login_required
def download_document(document_id):
    user = get_current_user()

    if not can_read_document(user.id, document_id):
        return jsonify({"error": "Document not found or access denied."}), 404

    doc = db.session.get(Document, document_id)
    path = UPLOAD_DIR / doc.stored_name

    if not path.is_file():
        return jsonify({"error": "Stored file is missing."}), 404

    audit_and_commit(
        user.id, doc.id, "document_downloaded",
        f"Downloaded {doc.original_name}"
    )

    return send_from_directory(
        UPLOAD_DIR,
        doc.stored_name,
        as_attachment=True,
        download_name=doc.original_name,
    )


@documents_bp.post("/<int:document_id>/share")
@login_required
def share_document(document_id):
    user = get_current_user()

    if not can_manage_document(user.id, document_id):
        return jsonify({"error": "Only the owner can share this document."}), 403

    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()

    if not email:
        return jsonify({"error": "Recipient email is required."}), 400

    recipient = User.query.filter_by(email=email).first()
    if recipient is None:
        return jsonify({"error": "Recipient must register first."}), 404

    if recipient.id == user.id:
        return jsonify({"error": "You already own this document."}), 400

    doc = db.session.get(Document, document_id)
    existing = DocumentShare.query.filter_by(
        document_id=doc.id, user_id=recipient.id
    ).first()

    try:
        if existing:
            existing.permission = "read"
        else:
            db.session.add(DocumentShare(
                document_id=doc.id,
                user_id=recipient.id,
                permission="read",
            ))

        record_audit(
            user.id, doc.id, "document_shared",
            f"Shared with {recipient.email} (read)"
        )
        db.session.commit()

        return jsonify({"message": "Document shared with read-only access."})

    except Exception:
        db.session.rollback()
        raise


@documents_bp.delete("/<int:document_id>")
@login_required
def delete_document(document_id):
    user = get_current_user()

    if not can_manage_document(user.id, document_id):
        return jsonify({"error": "Only the owner can delete this document."}), 403

    doc = db.session.get(Document, document_id)
    file_path = UPLOAD_DIR / doc.stored_name

    try:
        record_audit(
            user.id, doc.id, "document_deleted",
            f"Deleted {doc.original_name}"
        )

        DocumentShare.query.filter_by(document_id=doc.id).delete()
        db.session.delete(doc)
        db.session.commit()

        # Remove the physical file after the database transaction succeeds.
        if file_path.is_file():
            file_path.unlink()

        return jsonify({"message": "Document deleted successfully."})

    except Exception:
        db.session.rollback()
        raise
