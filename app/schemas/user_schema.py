from pydantic import BaseModel, EmailStr
from datetime import datetime
from uuid import UUID

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: UUID
    public_key: str
    created_at: datetime

    class Config:
        from_attributes = True
