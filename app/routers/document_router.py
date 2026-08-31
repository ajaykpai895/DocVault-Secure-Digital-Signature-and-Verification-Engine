import json
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from app.database import get_db
from app.services import document_service
from app.schemas.document_schema import DocumentResponse
from app.models.document import Document
from app.models.user import Role
from app.services.auth_service import get_current_user_dep
from app.models.audit import AuditAction
from app.utils.audit_logger import log_action

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentResponse)
def upload_document(
    metadata_json: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_dep()),
):
    """Upload a PDF. The owner_id is derived from the authenticated JWT token."""
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (limit is 10MB)")

    try:
        metadata = json.loads(metadata_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in metadata")

    try:
        doc = document_service.upload_document(db, file, current_user.id, metadata)
        log_action(db, AuditAction.UPLOAD, "SUCCESS",
                   document_id=doc.id, user_id=current_user.id,
                   detail=f"Uploaded '{doc.filename}'")
        db.commit()
        return doc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=Dict[str, Any])
def get_stats(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_dep()),
):
    """Return dashboard statistics."""
    from app.models.document import Document
    from app.models.audit import AuditLog
    
    # Filter by user if not admin
    if current_user.role == Role.ADMIN:
        docs = db.query(Document).all()
        audits = db.query(AuditLog).all()
    else:
        docs = db.query(Document).filter(Document.owner_id == current_user.id).all()
        # For audit logs, we'd only want those related to user's docs
        doc_ids = [d.id for d in docs]
        audits = db.query(AuditLog).filter(AuditLog.document_id.in_(doc_ids)).all() if doc_ids else []

    total_docs = len(docs)
    signed_docs = sum(1 for d in docs if d.status.value in ("SIGNED", "VERIFIED"))
    
    verify_attempts = sum(1 for a in audits if a.action.value == "VERIFY")
    tamper_alerts = sum(1 for a in audits if a.status == "TAMPERED")

    return {
        "total_documents": total_docs,
        "signed_this_month": signed_docs, # Simplify for now as signed documents
        "verification_attempts": verify_attempts,
        "tamper_alerts": tamper_alerts,
    }


from typing import Optional, List
from fastapi import Query
from sqlalchemy import or_

@router.get("", response_model=Dict[str, Any])
@router.get("/", response_model=Dict[str, Any])
def list_documents(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    sort: Optional[str] = "newest",
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_dep()),
):
    """List documents with pagination, filtering, and search."""
    from app.models.document import Document
    from app.models.user import User
    
    query = db.query(Document)
    
    if current_user.role != Role.ADMIN:
        query = query.filter(Document.owner_id == current_user.id)
        
    if search:
        search_pattern = f"%{search}%"
        # Try to parse search as UUID to search by ID, otherwise search by filename
        try:
            import uuid
            uuid_obj = uuid.UUID(search)
            query = query.filter(Document.id == str(uuid_obj))
        except ValueError:
            query = query.filter(Document.filename.ilike(search_pattern))
            
    if status and status != "ALL":
        statuses = status.split(",")
        query = query.filter(Document.status.in_(statuses))
        
    if sort == "newest":
        query = query.order_by(Document.created_at.desc())
    elif sort == "oldest":
        query = query.order_by(Document.created_at.asc())
    elif sort == "filename":
        query = query.order_by(Document.filename.asc())
        
    total = query.count()
    docs = query.offset((page - 1) * limit).limit(limit).all()

    # Attach owner usernames
    user_ids = list({d.owner_id for d in docs})
    users = {u.id: u.username for u in db.query(User).filter(User.id.in_(user_ids)).all()}

    for doc in docs:
        doc.owner_username = users.get(doc.owner_id)

    # Use DocumentResponse schema to serialize
    from app.schemas.document_schema import DocumentResponse
    items = [DocumentResponse.model_validate(doc).model_dump() for doc in docs]

    return {
        "total": total,
        "items": items,
        "page": page,
        "page_size": limit,
        "total_pages": (total + limit - 1) // limit
    }


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_dep()),
):
    doc = document_service.get_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    # Only the owner or admin can fetch document details
    if current_user.role != Role.ADMIN and doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return doc


@router.get("/{document_id}/metadata", response_model=Dict[str, Any])
def get_document_metadata(
    document_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_dep()),
):
    try:
        metadata = document_service.get_document_metadata(db, document_id, current_user.id)
        if metadata is None:
            raise HTTPException(status_code=404, detail="Document not found")
        return metadata
    except HTTPException:
        raise
    except ValueError as e:
        if str(e) == "Unauthorized":
            raise HTTPException(status_code=403, detail="Not authorized to view this document's metadata")
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Failed to decrypt metadata")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


from fastapi.responses import FileResponse
import os
from app.config import settings

@router.get("/{document_id}/download")
def download_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_dep()),
):
    doc = document_service.get_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if current_user.role != Role.ADMIN and doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # If document is signed, return the signed version. Otherwise original.
    uploads_dir = os.path.join(settings.STORAGE_PATH, "uploads")
    signed_path = os.path.join(uploads_dir, f"{document_id}_signed.pdf")
    original_path = os.path.join(uploads_dir, f"{document_id}.pdf")

    if os.path.exists(signed_path):
        return FileResponse(signed_path, media_type="application/pdf", filename=f"{doc.filename.replace('.pdf', '')}_signed.pdf")
    elif os.path.exists(original_path):
        return FileResponse(original_path, media_type="application/pdf", filename=doc.filename)
    else:
        raise HTTPException(status_code=404, detail="File not found on disk")


@router.get("/{document_id}/download/original")
def download_original_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_dep()),
):
    doc = document_service.get_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if current_user.role != Role.ADMIN and doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    uploads_dir = os.path.join(settings.STORAGE_PATH, "uploads")
    original_path = os.path.join(uploads_dir, f"{document_id}.pdf")

    if os.path.exists(original_path):
        return FileResponse(original_path, media_type="application/pdf", filename=doc.filename)
    else:
        raise HTTPException(status_code=404, detail="File not found on disk")
