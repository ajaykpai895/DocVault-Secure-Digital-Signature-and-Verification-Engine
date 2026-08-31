import os

base_dir = "c:/Users/HP/DocVault"

directories = [
    "app",
    "app/models",
    "app/schemas",
    "app/crypto",
    "app/routers",
    "app/services",
    "app/utils",
    "tests",
    "frontend",
    "storage",
    "storage/uploads",
    "storage/signed"
]

files = {
    "app/main.py": '"""FastAPI entrypoint for DocVault."""\n',
    "app/config.py": '"""Configuration, env vars, and settings."""\n',
    "app/database.py": '"""SQLAlchemy engine and session setup."""\n',
    "app/models/__init__.py": "",
    "app/models/user.py": '"""User and key pair model."""\n',
    "app/models/document.py": '"""Document model."""\n',
    "app/models/signature.py": '"""Signature record model."""\n',
    "app/schemas/__init__.py": "",
    "app/schemas/user_schema.py": '"""Pydantic schemas for User data."""\n',
    "app/schemas/document_schema.py": '"""Pydantic schemas for Document data."""\n',
    "app/schemas/signature_schema.py": '"""Pydantic schemas for Signature data."""\n',
    "app/crypto/__init__.py": "",
    "app/crypto/hash_engine.py": '"""SHA-512 hashing module."""\n',
    "app/crypto/key_manager.py": '"""ECDSA key generation and storage."""\n',
    "app/crypto/signature_engine.py": '"""ECDSA signature creation and verification."""\n',
    "app/crypto/metadata_cipher.py": '"""3DES encryption and decryption for metadata."""\n',
    "app/routers/__init__.py": "",
    "app/routers/auth_router.py": '"""Router for authentication endpoints."""\n',
    "app/routers/document_router.py": '"""Router for document upload and retrieval endpoints."""\n',
    "app/routers/signing_router.py": '"""Router for document signing endpoints."""\n',
    "app/routers/verification_router.py": '"""Router for document verification endpoints."""\n',
    "app/services/__init__.py": "",
    "app/services/document_service.py": '"""Service logic for handling documents."""\n',
    "app/services/signing_service.py": '"""Service logic for signing documents."""\n',
    "app/services/verification_service.py": '"""Service logic for verifying signatures."""\n',
    "app/utils/__init__.py": "",
    "app/utils/file_utils.py": '"""Utility functions for file handling."""\n',
    "app/utils/audit_logger.py": '"""Audit logging utilities."""\n',
    "tests/__init__.py": "",
    "tests/test_hash_engine.py": '"""Tests for the hash engine."""\n',
    "tests/test_signature_engine.py": '"""Tests for the signature engine."""\n',
    "tests/test_metadata_cipher.py": '"""Tests for the metadata cipher."""\n',
    "tests/test_document_flow.py": '"""Tests for the document upload and storage flow."""\n',
    "tests/test_verification_flow.py": '"""Tests for the document verification flow."""\n',
    "frontend/index.html": "<!-- DocVault Homepage -->\n",
    "frontend/upload.html": "<!-- Document Upload Page -->\n",
    "frontend/verify.html": "<!-- Document Verification Page -->\n",
    ".env.example": "",
    "requirements.txt": "",
    "README.md": "# DocVault\nSecure Digital Signature and Verification Engine\n",
    "run.sh": "#!/bin/bash\n# Run script for DocVault\n"
}

for d in directories:
    os.makedirs(os.path.join(base_dir, d), exist_ok=True)

for filepath, content in files.items():
    full_path = os.path.join(base_dir, filepath)
    if not os.path.exists(full_path):
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

print("Scaffolding complete.")
