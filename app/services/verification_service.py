import os
import shutil
import tempfile
import base64
import hmac
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import UploadFile
from pydantic import BaseModel

from app.models.document import Document, DocumentStatus
from app.models.signature import SignatureRecord
from app.models.user import User
from app.models.audit import AuditAction
from app.crypto.hash_engine import compute_file_hash
from app.crypto.key_manager import load_public_key
from app.crypto.signature_engine import verify_signature
from app.utils.audit_logger import log_action, log_verification_attempt


class VerificationResult(BaseModel):
    document_id: str
    hash_match: bool
    signature_valid: bool
    signer: Optional[str]
    signed_at: Optional[datetime]
    overall_status: str


def verify_document(db: Session, document_id: str, file: UploadFile, user_id: Optional[str] = None) -> VerificationResult:
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise ValueError("Document not found")

    # Save file temporarily to compute its hash
    fd, temp_path = tempfile.mkstemp()
    with os.fdopen(fd, 'wb') as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        current_hash = compute_file_hash(temp_path)
    finally:
        os.remove(temp_path)

    # Compare hashes using constant-time comparison
    hash_match = hmac.compare_digest(current_hash, doc.sha512_hash)

    if not hash_match:
        doc.status = DocumentStatus.TAMPERED
        log_action(db, AuditAction.VERIFY, "TAMPERED",
                   document_id=document_id, user_id=user_id,
                   detail="Hash mismatch — document may have been altered.")
        db.commit()
        log_verification_attempt(document_id, "TAMPERED")
        return VerificationResult(
            document_id=document_id,
            hash_match=False,
            signature_valid=False,
            signer=None,
            signed_at=None,
            overall_status="TAMPERED"
        )

    # Hash matches — fetch latest signature record
    sig = db.query(SignatureRecord).filter(
        SignatureRecord.document_id == document_id
    ).order_by(SignatureRecord.signed_at.desc()).first()

    if not sig:
        log_action(db, AuditAction.VERIFY, "NO_SIGNATURE",
                   document_id=document_id, user_id=user_id,
                   detail="File hash matches but no signature record found.")
        db.commit()
        log_verification_attempt(document_id, "NO_SIGNATURE")
        return VerificationResult(
            document_id=document_id,
            hash_match=True,
            signature_valid=False,
            signer=None,
            signed_at=None,
            overall_status="NO_SIGNATURE"
        )

    # Load public key and verify ECDSA signature
    user = db.query(User).filter(User.id == sig.signer_id).first()
    public_key = load_public_key(user.public_key.encode('utf-8'))
    signature_bytes = base64.b64decode(sig.signature_value)

    sig_valid = verify_signature(public_key, doc.sha512_hash, signature_bytes)

    if sig_valid:
        doc.status = DocumentStatus.VERIFIED
        sig.is_valid = True
        overall = "VALID"
    else:
        sig.is_valid = False
        overall = "INVALID_SIGNATURE"

    log_action(db, AuditAction.VERIFY, overall,
               document_id=document_id, user_id=user_id,
               detail=f"Verified by user_id={user_id}. Signer={user.username}.")
    db.commit()
    log_verification_attempt(document_id, overall, user.username)

    return VerificationResult(
        document_id=document_id,
        hash_match=True,
        signature_valid=sig_valid,
        signer=user.username,
        signed_at=sig.signed_at,
        overall_status=overall
    )
