from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.database import get_db
from app.models.user import User, Role
from app.models.audit import AuditLog, AuditAction
from app.services.auth_service import hash_password, verify_password, create_access_token
from app.crypto.key_manager import generate_key_pair

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: Optional[Role] = Role.OWNER


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    role: str


class UserProfile(BaseModel):
    id: str
    username: str
    email: str
    role: str


@router.post("/register", response_model=UserProfile, status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    # Check for existing username/email
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=409, detail="Username already taken")
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Generate ECDSA keypair locked with the user's password
    priv_pem, pub_pem = generate_key_pair(req.password.encode("utf-8"))

    user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
        public_key=pub_pem.decode("utf-8"),
        private_key_encrypted=priv_pem.decode("utf-8"),
        role=req.role,
    )
    db.add(user)
    db.flush()

    # Audit log
    db.add(AuditLog(
        user_id=user.id,
        action=AuditAction.REGISTER,
        status="SUCCESS",
        detail=f"New user registered: {user.username} with role {user.role.value}",
    ))
    db.commit()
    db.refresh(user)

    return UserProfile(id=user.id, username=user.username, email=user.email, role=user.role.value)


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    token = create_access_token({"sub": user.id, "role": user.role.value})

    db.add(AuditLog(
        user_id=user.id,
        action=AuditAction.LOGIN,
        status="SUCCESS",
        detail=f"User {user.username} logged in",
    ))
    db.commit()

    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
        role=user.role.value,
    )


from app.services.auth_service import get_current_user_dep

@router.get("/me", response_model=UserProfile)
def me(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user_dep())
):
    """Returns the currently authenticated user's profile."""
    return current_user
