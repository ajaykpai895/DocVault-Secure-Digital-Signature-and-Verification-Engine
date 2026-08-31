import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from io import BytesIO

from app.main import app
from app.database import Base, get_db
from app.models.user import User
from app.crypto.key_manager import generate_key_pair

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
    
    yield user.id
    
    db.delete(user)
    db.commit()
    db.close()

def test_get_document_metadata_success(setup_user):
    user_id = setup_user
    
    # Upload document
    file_content = b"This is a test PDF document."
    files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
    metadata = {"purpose": "test_metadata"}
    data = {
        "owner_id": user_id,
        "metadata_json": '{"purpose": "test_metadata"}'
    }
    
    upload_res = client.post("/documents/upload", data=data, files=files)
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["id"]
    
    # Get metadata
    metadata_res = client.get(f"/documents/{doc_id}/metadata", params={"requester_id": user_id})
    assert metadata_res.status_code == 200
    assert metadata_res.json() == metadata

def test_get_document_metadata_unauthorized(setup_user):
    user_id = setup_user
    
    # Upload document
    file_content = b"This is a test PDF document."
    files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
    data = {
        "owner_id": user_id,
        "metadata_json": '{"purpose": "test_metadata"}'
    }
    
    upload_res = client.post("/documents/upload", data=data, files=files)
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["id"]
    
    # Get metadata with wrong requester_id
    wrong_user_id = "some-other-uuid"
    metadata_res = client.get(f"/documents/{doc_id}/metadata", params={"requester_id": wrong_user_id})
    assert metadata_res.status_code == 403
    assert metadata_res.json()["detail"] == "Not authorized to view this document's metadata"

def test_get_document_metadata_not_found():
    metadata_res = client.get("/documents/non-existent-id/metadata", params={"requester_id": "any-id"})
    assert metadata_res.status_code == 404
