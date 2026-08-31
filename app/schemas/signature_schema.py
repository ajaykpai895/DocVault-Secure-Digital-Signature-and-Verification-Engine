from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional

class SignatureBase(BaseModel):
    document_id: UUID

class SignatureCreate(SignatureBase):
    signer_id: UUID

class SignatureResponse(SignatureBase):
    id: UUID
    document_id: UUID
    signer_id: UUID
    signature_value: str
    signed_hash: str
    signed_at: datetime
    is_valid: Optional[bool] = None

    class Config:
        from_attributes = True
