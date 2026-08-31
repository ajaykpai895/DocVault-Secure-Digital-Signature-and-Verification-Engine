# 🔐 DocVault — Cryptographic Document Security Platform

> A full-stack document signing and verification system built with **FastAPI**, **React 18**, and three real cryptographic algorithms: **SHA-512**, **ECDSA (SECP384R1)**, and **AES/3DES**.

---

## 📑 Table of Contents

- [Overview](#overview)
- [Screenshots](#screenshots)
- [Tech Stack](#tech-stack)
- [Cryptographic Architecture](#cryptographic-architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [How to Run](#how-to-run)
- [API Reference](#api-reference)
- [Running Tests](#running-tests)
- [Conclusion](#conclusion)

---

## 📖 Overview

**DocVault** is a security-focused document management platform that allows users to:

- 📤 **Upload** PDF documents securely with encrypted metadata
- ✍️ **Sign** documents using their personal ECDSA private key (encrypted at rest with their account password)
- ✅ **Verify** document authenticity and detect tampering using SHA-512 hash comparison and ECDSA signature verification
- 🗒️ **Audit** every action in a tamper-evident log — uploads, signings, and verifications are all recorded with timestamps and results

### Security Guarantees

- A signed document that has been modified even by a single byte is detected as **TAMPERED**
- Private keys **never leave the server unencrypted** — decrypted in memory only for the duration of signing
- Every user action is permanently recorded in a **tamper-evident audit trail**
- Passwords are hashed with **bcrypt** before storage — never stored in plaintext

---

## 📸 Screenshots

### 02 — Verify Document: Authentic ✅
> The SHA-512 hash matches exactly and the ECDSA signature is cryptographically valid against the signer's public key.

![Verify Authentic](screenshots/02_verify_authentic.png)

---

### 03 — Verify Document: Tampered ⚠️
> The SHA-512 hash of the re-uploaded file does not match the stored hash — the document has been altered after signing.

![Verify Tampered](screenshots/03_verify_tampered.png)

---

### 07 — System Audit Trail: Live Records
> A fully populated audit log showing 66 events — UPLOAD, SIGN, and VERIFY actions with timestamps, document IDs, actors, and colour-coded results (VALID / SUCCESS / TAMPERED).

![Audit Trail With Records](screenshots/07_audit_with_records.png)

---

### 06 — Audit Trail: Filter Panel (Full View)
> The audit log filter bar allowing users to narrow results by action type (Upload / Sign / Verify) and result status.

![Audit Filter Full](screenshots/06_audit_filter_full.png)

---

### 05 — Audit Trail: Filter (Compact View)
> Same filtering interface at a narrower viewport, demonstrating the responsive layout.

![Audit Filter](screenshots/05_audit_filter.png)

---

### 04 — Audit Trail: UI Layout
> The overall page structure of the System Audit Trail — header, filters, table columns, and empty state placeholder.

![Audit UI](screenshots/04_audit_trail_ui.png)

---

### 01 — Audit Trail: Early Development State
> The audit page captured during early development before the Vite proxy `/audit` route was configured.

![Audit Empty](screenshots/01_audit_trail_empty.png)

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend Framework** | Python 3.11+, FastAPI |
| **Database ORM** | SQLAlchemy + SQLite |
| **Frontend** | React 18, TypeScript, Vite |
| **Styling** | Tailwind CSS, custom design system |
| **HTTP Client** | Axios |
| **Cryptography** | PyCA `cryptography` library — ECDSA, SHA-512, AES/3DES |
| **Authentication** | JWT via `python-jose`, bcrypt password hashing |
| **PDF Processing** | PyMuPDF (`fitz`) |
| **Icons** | Lucide React |
| **Testing** | Pytest |

---

## 🔐 Cryptographic Architecture

DocVault uses **three cryptographic algorithms** in a layered security model.

---

### Algorithm 1 — SHA-512: Document Integrity Hashing
**File:** `app/services/document_service.py`

When a PDF is uploaded, its full binary content is hashed with **SHA-512** (produces a 512-bit / 128-character hex digest). This fingerprint is stored in the database alongside the document record.

On every verification request, the document is re-hashed and compared to the stored value:

```
SHA-512(document_bytes) → 128-hex-char digest → stored in DB

On verify:
  SHA-512(re-uploaded_bytes) == stored_hash?
    YES → Intact
    NO  → TAMPERED
```

Even a one-bit change to the document produces a completely different hash — making tampering instantly detectable.

---

### Algorithm 2 — ECDSA (SECP384R1): Digital Signatures
**File:** `app/services/signing_service.py`

When a user registers, an **ECDSA key pair** is generated on the **SECP384R1 (P-384)** elliptic curve. P-384 provides 192-bit security strength — equivalent to a 7680-bit RSA key.

- **Signing:** The SHA-512 hash of the document is signed with the user's private key
- **Verification:** The ECDSA signature is verified using the user's public key (stored in DB)

```
Private Key  →  sign(SHA-512_hash)     →  signature (embedded in PDF + stored in DB)
Public Key   →  verify(SHA-512_hash, signature) →  VALID / INVALID_SIGNATURE
```

---

### Algorithm 3 — AES / 3DES: Private Key Encryption at Rest
**File:** `app/crypto/key_manager.py`

The ECDSA private key is serialized to **PKCS#8** format and encrypted using `serialization.BestAvailableEncryption(password)` from the PyCA `cryptography` library (AES or 3DES depending on local OpenSSL version).

**The private key is never stored in plaintext.** It is decrypted in memory only for the instant of signing, then discarded.

```
ECDSA_private_key (PKCS#8)
  → AES/3DES encrypt with user's account password
  → encrypted blob stored in DB

On sign request:
  encrypted_blob + user_password → decrypt → private_key (in memory)
  → sign document hash → discard private_key from memory
```

---

### Complete Data Flow

```
REGISTRATION
  User registers → ECDSA key pair generated (SECP384R1)
                 → Private key encrypted (AES/3DES) with password → stored in DB
                 → Public key stored in DB

UPLOAD
  User uploads PDF → SHA-512 hash computed → hash + file stored

SIGN
  User enters password → Private key decrypted in memory
                       → SHA-512 hash of document signed (ECDSA)
                       → Signature embedded in PDF + stored in DB
                       → Private key discarded from memory

VERIFY
  File re-uploaded → SHA-512 computed → compared to stored hash
                   → If hash matches: ECDSA signature verified with public key
                   → Result: VALID / TAMPERED / INVALID_SIGNATURE
```

---

## 📁 Project Structure

```
DocVault/
├── app/                              # FastAPI backend
│   ├── main.py                       # App entry point, all route registration
│   ├── database.py                   # SQLAlchemy engine & session factory
│   ├── crypto/
│   │   ├── key_manager.py            # ECDSA key pair generation, AES/3DES encryption
│   │   └── metadata_cipher.py        # 3DES document metadata encryption
│   ├── models/
│   │   ├── user.py                   # User ORM model (id, username, hashed_password, keys)
│   │   ├── document.py               # Document ORM model (id, hash, status, owner)
│   │   ├── signature.py              # Signature ORM model (sig bytes, signer, timestamp)
│   │   └── audit.py                  # AuditLog ORM model (action, status, detail, timestamp)
│   ├── routers/
│   │   ├── auth_router.py            # POST /auth/register, /auth/login, GET /auth/me
│   │   ├── document_router.py        # POST /documents/upload, GET /documents, /stats
│   │   ├── signing_router.py         # POST /documents/{id}/sign
│   │   └── verification_router.py    # POST /documents/{id}/verify
│   ├── schemas/
│   │   ├── user_schema.py            # Pydantic user request/response models
│   │   └── document_schema.py        # Pydantic document request/response models
│   ├── services/
│   │   ├── auth_service.py           # JWT creation, bcrypt password hashing
│   │   ├── document_service.py       # Upload logic, SHA-512 hashing
│   │   ├── signing_service.py        # ECDSA signing workflow
│   │   └── verification_service.py   # Hash comparison + signature verification
│   └── utils/
│       └── audit_logger.py           # Centralised audit event logger
│
├── docvault-react/                   # React + TypeScript frontend
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx         # Stats cards overview
│   │   │   ├── Upload.tsx            # PDF upload form
│   │   │   ├── Sign.tsx              # Sign document with private key
│   │   │   ├── Verify.tsx            # Verify document integrity & signature
│   │   │   ├── Documents.tsx         # Paginated document list
│   │   │   ├── Audit.tsx             # System audit trail with filters
│   │   │   ├── Login.tsx             # Auth login page
│   │   │   └── Register.tsx          # New user registration page
│   │   ├── components/
│   │   │   ├── Layout.tsx            # Navigation shell + route protection
│   │   │   ├── ProtectedRoute.tsx    # JWT auth guard
│   │   │   └── ui/                   # Reusable Badge, Skeleton, etc.
│   │   ├── contexts/
│   │   │   └── AuthContext.tsx       # Global JWT auth state
│   │   └── lib/
│   │       ├── api.ts                # Axios instance with JWT interceptor
│   │       └── utils.ts              # getErrorMessage() helper
│   ├── vite.config.ts                # Vite dev server & API proxy config
│   └── package.json
│
├── tests/                            # Pytest unit & integration tests
│   ├── test_hash_engine.py           # SHA-512 consistency & tamper detection
│   ├── test_signature_engine.py      # ECDSA sign + verify round-trips
│   ├── test_metadata_cipher.py       # 3DES encryption/decryption
│   ├── test_document_flow.py         # Full upload → sign flow
│   └── test_verification_flow.py     # Full verify + tamper detection
│
├── storage/
│   ├── uploads/                      # Original uploaded PDF files
│   └── signed/                       # Signed PDF copies with embedded signatures
│
├── screenshots/                      # UI screenshots (used in this README)
│   ├── 01_audit_trail_empty.png
│   ├── 02_verify_authentic.png
│   ├── 03_verify_tampered.png
│   ├── 04_audit_trail_ui.png
│   ├── 05_audit_filter.png
│   ├── 06_audit_filter_full.png
│   └── 07_audit_with_records.png
│
├── docvault.db                       # SQLite database (auto-created on first run)
├── requirements.txt                  # Python dependencies
├── setup_demo_docs.py                # Script to seed demo data
└── README.md
```

---

## ✅ Prerequisites

Make sure the following are installed before you begin:

- [Python 3.11+](https://www.python.org/downloads/)
- [Node.js 18+ and npm](https://nodejs.org/)
- [Git](https://git-scm.com/)

---

## ⚙️ Installation & Setup

### Step 1 — Clone the repository

```bash
git clone https://github.com/your-username/DocVault.git
cd DocVault
```

### Step 2 — Set up the Python backend

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS / Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3 — Set up the React frontend

```bash
cd docvault-react
npm install
cd ..
```

---

## ▶️ How to Run

Open **two separate terminals** from inside the `DocVault` folder.

### Terminal 1 — Backend Server

```bash
# Windows
venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# macOS / Linux
venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

| | URL |
|---|---|
| **API Base** | `http://127.0.0.1:8000` |
| **Swagger Docs** | `http://127.0.0.1:8000/docs` |
| **ReDoc** | `http://127.0.0.1:8000/redoc` |

### Terminal 2 — Frontend Dev Server

```bash
cd docvault-react
npm run dev
```

| | URL |
|---|---|
| **Frontend** | `http://localhost:5173` |

> If port 5173 is busy, Vite will automatically try `5174`, etc. Check terminal output.

### 🔑 Default Login

| Field | Value |
|-------|-------|
| **Username** | `testuser_e2e` |
| **Password** | `mypassword123` |

Or register a new account at `/register` — this automatically generates your personal ECDSA key pair.

---

## 📡 API Reference

All endpoints (except `/auth/*`) require a `Bearer` JWT token in the `Authorization` header.

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/auth/register` | No | Register new user, generates ECDSA key pair |
| `POST` | `/auth/login` | No | Login, returns JWT access token |
| `GET` | `/auth/me` | Yes | Get current user profile |
| `POST` | `/documents/upload` | Yes | Upload a PDF document |
| `GET` | `/documents` | Yes | List all documents for current user |
| `GET` | `/documents/stats` | Yes | Dashboard statistics |
| `GET` | `/documents/{id}` | Yes | Get a single document |
| `GET` | `/documents/{id}/download` | Yes | Download the signed PDF |
| `POST` | `/documents/{id}/sign` | Yes | Sign document with private key (form: `private_key_password`) |
| `POST` | `/documents/{id}/verify` | Yes | Verify document integrity and signature |
| `GET` | `/audit` | Yes | Get all audit log entries for current user |

Interactive API docs available at **`http://127.0.0.1:8000/docs`** when the server is running.

---

## 🧪 Running Tests

```bash
# Activate virtual environment first
venv\Scripts\activate      # Windows
source venv/bin/activate   # macOS / Linux

# Run all tests with verbose output
pytest tests/ -v

# Run specific test files
pytest tests/test_hash_engine.py -v
pytest tests/test_signature_engine.py -v
pytest tests/test_metadata_cipher.py -v
pytest tests/test_document_flow.py -v
pytest tests/test_verification_flow.py -v
```

### Test Coverage

| Test File | What It Covers |
|-----------|----------------|
| `test_hash_engine.py` | SHA-512 consistency, determinism, tamper detection |
| `test_signature_engine.py` | ECDSA key generation, sign + verify round-trips |
| `test_metadata_cipher.py` | 3DES encrypt / decrypt correctness |
| `test_document_flow.py` | Full upload → sign workflow |
| `test_verification_flow.py` | Valid verification + tampered file detection |

---

## 🏁 Conclusion

DocVault demonstrates the practical, real-world application of cryptographic principles in a full-stack production-style system.

### What this project proves

| Property | How it is Achieved |
|----------|--------------------|
| **Integrity** | SHA-512 hashing — any change to a document, even a single byte, produces a completely different hash and is instantly detected |
| **Authenticity** | ECDSA digital signatures — only the holder of the encrypted private key can produce a valid signature for a document |
| **Key Confidentiality** | AES/3DES encryption at rest — private keys are stored encrypted and are only decrypted in memory for the duration of signing |
| **Non-repudiation** | The tamper-evident audit trail records every upload, signing, and verification with the actor's identity, timestamp, and result |
| **Password Safety** | bcrypt hashing — user passwords are never stored or transmitted in plaintext |

### Design philosophy

DocVault was designed around the principle that security should be **transparent and legible** to the end user. The verify page tells you exactly why a document is valid or invalid (showing the hash comparison and signer identity), and the audit log gives complete visibility into every operation performed on every document.

This project was built to explore applied cryptography in the context of **legal-tech and document management**, where the authenticity and integrity of files is a first-class concern.

---

*Built with FastAPI · React 18 · ECDSA (P-384) · SHA-512 · AES/3DES · SQLite*
