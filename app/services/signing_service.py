import os
import io
import uuid
import base64
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.models.signature import SignatureRecord
from app.models.audit import AuditAction
from app.crypto.key_manager import load_private_key
from app.crypto.signature_engine import sign_hash
from app.utils.audit_logger import log_action
from app.config import settings

from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import qrcode
from PIL import Image


def sign_document(db: Session, document_id: str, signer_id: str, private_key_password: str) -> SignatureRecord:
    # Fetch Document
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise ValueError("Document not found")

    # Fetch User
    user = db.query(User).filter(User.id == signer_id).first()
    if not user:
        raise ValueError("Signer not found")

    # Load private key
    try:
        private_key = load_private_key(
            user.private_key_encrypted.encode('utf-8'),
            private_key_password.encode('utf-8')
        )
    except Exception as e:
        raise ValueError(f"Failed to unlock private key: {str(e)}")

    # Sign the document hash
    signature_bytes = sign_hash(private_key, document.sha512_hash)
    signature_b64 = base64.b64encode(signature_bytes).decode('utf-8')

    # Store SignatureRecord
    sig_id = str(uuid.uuid4())
    sig_record = SignatureRecord(
        id=sig_id,
        document_id=document_id,
        signer_id=signer_id,
        signature_value=signature_b64,
        signed_hash=document.sha512_hash,
        is_valid=True
    )

    document.status = DocumentStatus.SIGNED
    db.add(sig_record)

    # Audit log — atomically committed with the signature record
    log_action(db, AuditAction.SIGN, "SUCCESS",
               document_id=document_id, user_id=signer_id,
               detail=f"Document signed by {user.username}. Sig ID: {sig_id}")

    db.commit()
    db.refresh(sig_record)

    # Generate Certified PDF with a signature stamp + QR code
    _stamp_pdf(document, user, sig_record)

    return sig_record


def _stamp_pdf(document: Document, user: User, signature: SignatureRecord):
    """
    Appends a visible certificate page (with QR code) to the end of the PDF.
    The QR code encodes a deep-link to the public verify endpoint.
    """
    signed_dir = os.path.join(settings.STORAGE_PATH, "signed")
    os.makedirs(signed_dir, exist_ok=True)
    out_path = os.path.join(signed_dir, f"{document.id}_signed.pdf")

    # --- Build QR code ---
    verify_url = f"http://localhost:8000/documents/{document.id}/verify-qr"
    qr = qrcode.QRCode(version=1, box_size=4, border=2)
    qr.add_data(verify_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    import tempfile
    qr_tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    qr_img.save(qr_tmp.name, format="PNG")
    qr_tmp.close()
    qr_path = qr_tmp.name

    # --- Build certificate page using ReportLab ---
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)

    # Title bar
    can.setFillColorRGB(0.1, 0.1, 0.3)
    can.rect(30, 720, 550, 50, fill=True, stroke=False)
    can.setFillColorRGB(1, 1, 1)
    can.setFont("Helvetica-Bold", 18)
    can.drawString(50, 737, "DocVault — Digital Signature Certificate")

    # Certificate fields
    can.setFillColorRGB(0, 0, 0)
    can.setFont("Helvetica-Bold", 11)
    can.drawString(50, 700, "Signer:")
    can.setFont("Helvetica", 11)
    can.drawString(140, 700, f"{user.username} ({user.email})")

    can.setFont("Helvetica-Bold", 11)
    can.drawString(50, 680, "Date Signed:")
    can.setFont("Helvetica", 11)
    can.drawString(140, 680, str(signature.signed_at or datetime.now()))

    can.setFont("Helvetica-Bold", 11)
    can.drawString(50, 660, "Document ID:")
    can.setFont("Helvetica", 11)
    can.drawString(140, 660, document.id)

    can.setFont("Helvetica-Bold", 11)
    can.drawString(50, 640, "Signature Ref:")
    can.setFont("Helvetica", 11)
    can.drawString(140, 640, signature.id)

    can.setFont("Helvetica-Bold", 11)
    can.drawString(50, 620, "SHA-512 Hash:")
    can.setFont("Helvetica", 9)
    can.drawString(50, 606, document.sha512_hash[:64])
    can.drawString(50, 594, document.sha512_hash[64:])

    # QR Code — use file path instead of BytesIO
    can.drawImage(qr_path, 410, 560, width=120, height=120)
    can.setFont("Helvetica", 8)
    can.drawString(405, 553, "Scan to verify online")

    # Footer
    can.setFillColorRGB(0.5, 0.5, 0.5)
    can.setFont("Helvetica-Oblique", 9)
    can.drawString(50, 530, "This page was automatically appended by DocVault to certify cryptographic authenticity.")
    can.save()

    packet.seek(0)
    cert_pdf = PdfReader(packet)

    # Read the original PDF and append the cert page
    original_pdf = PdfReader(document.file_path)
    writer = PdfWriter()

    for page in original_pdf.pages:
        writer.add_page(page)

    writer.add_page(cert_pdf.pages[0])

    with open(out_path, "wb") as output_pdf:
        writer.write(output_pdf)

    # Clean up temp QR file
    import os as _os
    try:
        _os.unlink(qr_path)
    except Exception:
        pass
