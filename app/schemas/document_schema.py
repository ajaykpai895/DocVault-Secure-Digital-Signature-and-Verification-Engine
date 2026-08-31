from pydantic import BaseModel, computed_field
from datetime import datetime
from uuid import UUID
from app.models.document import DocumentStatus
from typing import Optional, List

class DocumentBase(BaseModel):
    filename: str

class DocumentCreate(DocumentBase):
    owner_id: UUID

class DocumentResponse(DocumentBase):
    id: UUID
    owner_id: UUID
    filename: str
    sha512_hash: str
    status: DocumentStatus
    created_at: datetime
    owner_username: Optional[str] = None  # populated by list endpoint

    @property
    def uploaded_at(self) -> datetime:
        return self.created_at

    class Config:
        from_attributes = True

class DocumentListResponse(BaseModel):
    total: int
    items: List[DocumentResponse]
    page: int
    page_size: int
    total_pages: int
