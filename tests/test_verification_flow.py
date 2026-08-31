import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from io import BytesIO

from app.main import app
from app.database import Base, get_db
from app.models.user import User
from app.crypto.key_manager import generate_key_pair

# Set up test DB
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_docvault.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture
def setup_user():
    db = TestingSessionLocal()
    password = b"test_pass"
    priv_pem, pub_pem = generate_key_pair(password)
    
    user = User(
        username="test_user",
        email="test@example.com",
        public_key=pub_pem.decode('utf-8'),
        private_key_encrypted=priv_pem.decode('utf-8')
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    yield user.id, "test_pass"
    
    # cleanup
    db.delete(user)
    db.commit()
    db.close()

from reportlab.pdfgen import canvas

def create_test_pdf(text="Test PDF"):
    packet = BytesIO()
    can = canvas.Canvas(packet)
    can.drawString(10, 100, text)
    can.save()
    packet.seek(0)
    return packet.read()

def test_full_verification_flow_valid(setup_user):
    user_id, password = setup_user
    
    # 1. Upload Document
    file_content = create_test_pdf()
    files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
    data = {
        "owner_id": user_id,
        "metadata_json": '{"purpose": "test"}'
    }
    
    upload_res = client.post("/documents/upload", data=data, files=files)
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["id"]
    
    # 2. Sign Document
    sign_data = {
        "signer_id": user_id,
        "private_key_password": password
    }
    sign_res = client.post(f"/documents/{doc_id}/sign", data=sign_data)
    assert sign_res.status_code == 200, f"Failed to sign: {sign_res.text}"
    
    # 3. Verify Document (Unmodified)
    files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
    verify_res = client.post(f"/documents/{doc_id}/verify", files=files)
    assert verify_res.status_code == 200
    result = verify_res.json()
    assert result["overall_status"] == "VALID"
    assert result["hash_match"] is True
    assert result["signature_valid"] is True

def test_full_verification_flow_tampered(setup_user):
    user_id, password = setup_user
    
    # 1. Upload Document
    file_content = create_test_pdf("Another test")
    files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
    data = {
        "owner_id": user_id,
        "metadata_json": '{"purpose": "test"}'
    }
    
    upload_res = client.post("/documents/upload", data=data, files=files)
    doc_id = upload_res.json()["id"]
    
    # 2. Sign Document
    sign_data = {
        "signer_id": user_id,
        "private_key_password": password
    }
    client.post(f"/documents/{doc_id}/sign", data=sign_data)
    
    # 3. Verify Document (Modified)
    modified_content = create_test_pdf("Another test BUT TAMPERED")
    files = {"file": ("test.pdf", BytesIO(modified_content), "application/pdf")}
    verify_res = client.post(f"/documents/{doc_id}/verify", files=files)
    assert verify_res.status_code == 200
    result = verify_res.json()
    assert result["overall_status"] == "TAMPERED"
    assert result["hash_match"] is False
    assert result["signature_valid"] is False

def test_full_verification_flow_invalid_signature(setup_user):
    user_id, password = setup_user
    
    # 1. Upload Document
    file_content = create_test_pdf("Bad signature test")
    files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
    data = {
        "owner_id": user_id,
        "metadata_json": '{"purpose": "test"}'
    }
    
    upload_res = client.post("/documents/upload", data=data, files=files)
    doc_id = upload_res.json()["id"]
    
    # 2. Sign Document
    sign_data = {
        "signer_id": user_id,
        "private_key_password": password
    }
    client.post(f"/documents/{doc_id}/sign", data=sign_data)
    
    # Manually corrupt the signature in the DB to test INVALID_SIGNATURE
    db = TestingSessionLocal()
    from app.models.signature import SignatureRecord
    sig = db.query(SignatureRecord).filter(SignatureRecord.document_id == doc_id).first()
    import base64
    raw = base64.b64decode(sig.signature_value)
    # flip a byte
    corrupted = (raw[0] ^ 1).to_bytes(1, 'big') + raw[1:]
    sig.signature_value = base64.b64encode(corrupted).decode('utf-8')
    db.commit()
    db.close()
    
    # 3. Verify Document (Unmodified file, but bad signature in DB)
    files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
    verify_res = client.post(f"/documents/{doc_id}/verify", files=files)
    assert verify_res.status_code == 200
    result = verify_res.json()
    assert result["overall_status"] == "INVALID_SIGNATURE"
    assert result["hash_match"] is True
    assert result["signature_valid"] is False
