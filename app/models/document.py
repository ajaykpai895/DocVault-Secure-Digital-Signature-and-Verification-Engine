import uuid
import enum
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.sql import func
from app.database import Base

class DocumentStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    SIGNED = "SIGNED"
    VERIFIED = "VERIFIED"
    TAMPERED = "TAMPERED"

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    sha512_hash = Column(String(128), nullable=False, index=True)
    encrypted_metadata = Column(Text, nullable=False)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.UPLOADED, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
