import uuid
import enum
from sqlalchemy import Column, String, DateTime, Text, Enum
from sqlalchemy.sql import func
from app.database import Base

class Role(str, enum.Enum):
    OWNER = "OWNER"
    VERIFIER = "VERIFIER"
    ADMIN = "ADMIN"

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    public_key = Column(Text, nullable=False)
    private_key_encrypted = Column(Text, nullable=False)
    role = Column(Enum(Role), default=Role.OWNER, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
