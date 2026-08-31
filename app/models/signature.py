import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.sql import func
from app.database import Base

class SignatureRecord(Base):
    __tablename__ = "signatures"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    signer_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    signature_value = Column(Text, nullable=False)
    signed_hash = Column(String(128), nullable=False)
    signed_at = Column(DateTime(timezone=True), server_default=func.now())
    is_valid = Column(Boolean, nullable=True)
