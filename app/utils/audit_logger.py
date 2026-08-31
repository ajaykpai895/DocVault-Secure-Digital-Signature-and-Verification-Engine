from sqlalchemy.orm import Session
from typing import Optional
from app.models.audit import AuditLog, AuditAction


def log_action(
    db: Session,
    action: AuditAction,
    status: str,
    document_id: Optional[str] = None,
    user_id: Optional[str] = None,
    detail: Optional[str] = None,
    ip_address: Optional[str] = None,
):
    """
    Persists an audit event to the database.
    Does NOT expose private keys or raw metadata in the detail field.
    """
    entry = AuditLog(
        document_id=document_id,
        user_id=user_id,
        action=action,
        status=status,
        detail=detail,
        ip_address=ip_address,
    )
    db.add(entry)
    # We do NOT commit here — the caller commits their own transaction
    # so audit entries are atomic with the action they record.


def log_verification_attempt(document_id: str, status: str, signer: str = None):
    """
    Legacy stdout logger kept for backwards compatibility with existing callers.
    """
    import logging
    logger = logging.getLogger("DocVault_Audit")
    msg = f"Verification attempt for Document ID: {document_id} resulted in status: {status}."
    if signer:
        msg += f" Signer: {signer}."
    logger.info(msg)
