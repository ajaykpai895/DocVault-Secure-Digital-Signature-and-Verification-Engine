from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import verification_service
from app.models.document import Document
from app.services.auth_service import get_current_user_dep

router = APIRouter(prefix="/documents", tags=["Verification"])


@router.post("/{document_id}/verify", response_model=verification_service.VerificationResult)
def verify_document(
    document_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_dep()),
):
    """
    Verifies a document's integrity and signature.
    Any authenticated user (Owner, Verifier, Admin) can verify.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (limit is 10MB)")

    try:
        result = verification_service.verify_document(db, document_id, file, user_id=current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/status")
def get_document_status(
    document_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_dep()),
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"document_id": document_id, "status": doc.status.value}
