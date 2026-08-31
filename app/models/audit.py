import uuid
import datetime
import enum
from sqlalchemy import Column, String, DateTime, Text, Enum, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class AuditAction(str, enum.Enum):
    UPLOAD = "UPLOAD"
    SIGN = "SIGN"
    VERIFY = "VERIFY"
    LOGIN = "LOGIN"
    REGISTER = "REGISTER"

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(Enum(AuditAction), nullable=False)
    status = Column(String(50), nullable=False)  # e.g. VALID, TAMPERED, SUCCESS
    detail = Column(Text, nullable=True)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
