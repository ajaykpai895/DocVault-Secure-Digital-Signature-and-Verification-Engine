from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime
import os

from app.database import Base, engine, get_db
from app.routers import document_router, signing_router, verification_router, auth_router
from app.models.audit import AuditLog
from app.services.auth_service import get_current_user_dep

# Create all tables (including new AuditLog, updated User with role/hashed_password)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="DocVault",
    description="Secure Digital Signature and Verification Engine",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ─────────────────────────────────────────────────────────────
app.include_router(auth_router.router)
app.include_router(document_router.router)
app.include_router(signing_router.router)
app.include_router(verification_router.router)


# ── Health ───────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "message": "DocVault engine is running.", "version": "2.0.0"}


# ── Audit Trail Endpoint ──────────────────────────────────────────────────
class AuditEntry(BaseModel):
    id: str
    document_id: str | None
    user_id: str | None
    action: str
    status: str
    detail: str | None
    created_at: datetime | None

    class Config:
        from_attributes = True


@app.get("/documents/{document_id}/audit", response_model=List[AuditEntry], tags=["Audit"])
def get_audit_trail(
    document_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_dep()),
):
    """
    Returns the full audit trail for a document.
    Accessible by: OWNER of the document, or ADMIN.
    """
    from app.models.document import Document
    from app.models.user import Role

    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if current_user.role != Role.ADMIN and doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this document's audit trail")

    logs = (
        db.query(AuditLog)
        .filter(AuditLog.document_id == document_id)
        .order_by(AuditLog.created_at.asc())
        .all()
    )
    return logs


@app.get("/audit", response_model=List[AuditEntry], tags=["Audit"])
def get_all_audit_logs(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_dep()),
):
    """
    Returns all audit logs in the system.
    If current_user is ADMIN, returns all.
    Otherwise, returns only logs for documents owned by the current_user.
    """
    from app.models.document import Document
    from app.models.user import Role

    query = db.query(AuditLog).order_by(AuditLog.created_at.desc())

    if current_user.role != Role.ADMIN:
        # Join with Document to filter by owner_id
        query = query.join(Document, AuditLog.document_id == Document.id).filter(Document.owner_id == current_user.id)

    logs = query.all()
    return logs


# ── QR Quick-Verify Endpoint (public, no auth required) ──────────────────
@app.get("/documents/{document_id}/verify-qr", tags=["Verification"])
def qr_verify_redirect(document_id: str, db: Session = Depends(get_db)):
    """
    Called when a user scans the QR code on a printed document.
    Returns a quick status summary without requiring the original file upload.
    """
    from app.models.document import Document
    from app.models.signature import SignatureRecord

    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    sig = (
        db.query(SignatureRecord)
        .filter(SignatureRecord.document_id == document_id)
        .order_by(SignatureRecord.signed_at.desc())
        .first()
    )

    from app.models.user import User
    signer_name = None
    if sig:
        signer = db.query(User).filter(User.id == sig.signer_id).first()
        signer_name = signer.username if signer else None

    return {
        "document_id": document_id,
        "filename": doc.filename,
        "status": doc.status.value,
        "signer": signer_name,
        "signed_at": sig.signed_at.isoformat() if sig and sig.signed_at else None,
        "message": (
            "This document was cryptographically signed and verified via DocVault."
            if doc.status.value == "VERIFIED"
            else f"Document status: {doc.status.value}. Upload the file to run a full verification."
        ),
    }


# ── SPA Frontend serving (must be AFTER all API routes) ──────────────────
# Serve /assets/* statically (JS, CSS, images from React build)
_frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

if os.path.isdir(_frontend_path):
    _assets_path = os.path.join(_frontend_path, "assets")
    if os.path.isdir(_assets_path):
        app.mount("/assets", StaticFiles(directory=_assets_path), name="assets")

    # Root and all other paths → return index.html for React Router to handle
    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str = ""):
        # Never catch API or docs paths — only serve the SPA for unknown routes
        if full_path.startswith(("api/", "docs", "openapi", "health", "auth/", "documents/")):
            raise HTTPException(status_code=404, detail="Not found")
        index = os.path.join(_frontend_path, "index.html")
        if os.path.exists(index):
            return FileResponse(index)
        raise HTTPException(status_code=404, detail="Frontend not built yet")
