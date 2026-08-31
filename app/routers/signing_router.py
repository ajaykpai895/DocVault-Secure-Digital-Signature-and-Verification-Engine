from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import signing_service
from app.schemas.signature_schema import SignatureResponse
from app.services.auth_service import get_current_user_dep
from app.models.user import Role

router = APIRouter(prefix="/documents", tags=["Signing"])


@router.post("/{document_id}/sign", response_model=SignatureResponse)
def sign_document(
    document_id: str,
    private_key_password: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_dep()),
):
    """
    Signs a document. Only the document owner or an Admin can sign.
    The signer_id is taken from the authenticated JWT token — no need to pass it manually.
    """
    try:
        # Verify ownership or admin role
        from app.models.document import Document
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        if current_user.role != Role.ADMIN and doc.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Only the document owner can sign it")

        signature = signing_service.sign_document(db, document_id, current_user.id, private_key_password)
        return signature
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
