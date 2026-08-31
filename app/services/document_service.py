import os
import uuid
import json
import shutil
from sqlalchemy.orm import Session
from fastapi import UploadFile
from app.models.document import Document, DocumentStatus
from app.crypto.hash_engine import compute_file_hash
from app.crypto.metadata_cipher import encrypt_metadata, decrypt_metadata
from app.config import settings

def upload_document(db: Session, file: UploadFile, owner_id: str, metadata: dict) -> Document:
    """
    Saves the uploaded PDF, computes its hash, encrypts the metadata,
    and persists a new Document record.
    """
    document_id = str(uuid.uuid4())
    
    # Ensure storage directory exists
    uploads_dir = os.path.join(settings.STORAGE_PATH, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    
    file_path = os.path.join(uploads_dir, f"{document_id}.pdf")
    
    # Save the file to disk
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Compute SHA-512 hash
    sha512_hash = compute_file_hash(file_path)
    
    # Encrypt metadata
    metadata_json = json.dumps(metadata)
    master_key = settings.DES3_MASTER_KEY.encode('utf-8')
    # Pad key to 24 bytes if necessary, or assume it's exactly 24 bytes
    if len(master_key) != 24:
        master_key = master_key.ljust(24, b'0')[:24]
        
    encrypted_meta = encrypt_metadata(metadata_json, master_key)
    
    # Create DB record
    db_doc = Document(
        id=document_id,
        owner_id=owner_id,
        filename=file.filename,
        file_path=file_path,
        sha512_hash=sha512_hash,
        encrypted_metadata=encrypted_meta,
        status=DocumentStatus.UPLOADED
    )
    
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    
    return db_doc

def get_document(db: Session, document_id: str) -> Document:
    return db.query(Document).filter(Document.id == document_id).first()

def get_document_metadata(db: Session, document_id: str, requester_id: str) -> dict:
    """
    Retrieves and decrypts a document's metadata if the requester is authorized.
    """
    doc = get_document(db, document_id)
    if not doc:
        return None
        
    if doc.owner_id != requester_id:
        raise ValueError("Unauthorized")
        
    master_key = settings.DES3_MASTER_KEY.encode('utf-8')
    if len(master_key) != 24:
        master_key = master_key.ljust(24, b'0')[:24]
        
    try:
        metadata_json_str = decrypt_metadata(doc.encrypted_metadata, master_key)
        return json.loads(metadata_json_str)
    except Exception as e:
        raise RuntimeError(f"Failed to decrypt metadata: {str(e)}")
