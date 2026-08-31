"""
setup_demo_docs.py
------------------
Creates three demo PDFs and wires them into DocVault via the API:

  1. contract_verified.pdf   → uploaded, signed, then verified  (status: VERIFIED)
  2. report_tampered.pdf     → uploaded, signed, then the raw file is byte-edited
                               so the next verify call returns TAMPERED
  3. agreement_to_sign.pdf   → uploaded only, awaiting signature  (status: UPLOADED)
"""

import io
import json
import os
import sys
import requests
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

BASE = "http://127.0.0.1:8000"
USERNAME = "testuser_e2e"
PASSWORD = "mypassword123"

# ── helpers ──────────────────────────────────────────────────────────────────

def login():
    r = requests.post(f"{BASE}/auth/login",
                      data={"username": USERNAME, "password": PASSWORD},
                      headers={"Content-Type": "application/x-www-form-urlencoded"})
    r.raise_for_status()
    token = r.json()["access_token"]
    print(f"  Logged in as {USERNAME}")
    return token

def auth(token):
    return {"Authorization": f"Bearer {token}"}

def make_pdf_bytes(title: str, body_paragraphs: list[str]) -> bytes:
    """Render a PDF in-memory using ReportLab and return raw bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2.5*cm, rightMargin=2.5*cm,
        topMargin=2.5*cm, bottomMargin=2.5*cm,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Title"],
        fontSize=20,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "Sub",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=16,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=11,
        leading=17,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=10,
    )
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#94a3b8"),
        alignment=1,
    )

    story = [
        Paragraph("DocVault", subtitle_style),
        Paragraph(title, title_style),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceAfter=20),
    ]
    for para in body_paragraphs:
        story.append(Paragraph(para, body_style))
    story.append(Spacer(1, 2*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceAfter=8))
    story.append(Paragraph("Secured with SHA-512 · ECDSA · 3DES &nbsp;|&nbsp; DocVault", footer_style))

    doc.build(story)
    return buf.getvalue()


def upload(token, filename, pdf_bytes, owner, classification, purpose):
    meta = json.dumps({
        "owner_name": owner,
        "classification": classification,
        "purpose": purpose,
    })
    r = requests.post(
        f"{BASE}/documents/upload",
        headers=auth(token),
        files={"file": (filename, pdf_bytes, "application/pdf")},
        data={"metadata_json": meta},
    )
    r.raise_for_status()
    doc = r.json()
    print(f"  Uploaded '{filename}'  ->  id={doc['id']}")
    return doc

def sign(token, doc_id):
    r = requests.post(
        f"{BASE}/documents/{doc_id}/sign",
        headers=auth(token),
        data={"private_key_password": PASSWORD},
    )
    r.raise_for_status()
    print(f"  Signed   doc_id={doc_id[:8]}...")
    return r.json()

def verify(token, doc_id, pdf_bytes):
    r = requests.post(
        f"{BASE}/documents/{doc_id}/verify",
        headers=auth(token),
        files={"file": ("verify.pdf", pdf_bytes, "application/pdf")},
    )
    r.raise_for_status()
    result = r.json()
    print(f"  Verified doc_id={doc_id[:8]}...  ->  result={result.get('result', result)}")
    return result


# ── PDF content ───────────────────────────────────────────────────────────────

CONTRACT_BODY = [
    "This Non-Disclosure Agreement (\"Agreement\") is entered into as of the date of "
    "digital signature between the undersigned parties.",

    "1. <b>Confidential Information.</b> Each party may disclose to the other certain "
    "confidential technical and business information which the disclosing party desires "
    "the receiving party to treat as confidential.",

    "2. <b>Obligations.</b> The receiving party agrees to: (a) hold the Confidential "
    "Information in strict confidence; (b) not disclose the Confidential Information to "
    "any third parties without prior written consent; (c) use the Confidential Information "
    "solely for the purposes of evaluating a potential business relationship.",

    "3. <b>Term.</b> This Agreement shall remain in effect for a period of three (3) years "
    "from the date of execution unless earlier terminated by mutual written agreement.",

    "4. <b>Governing Law.</b> This Agreement shall be governed by and construed in accordance "
    "with applicable law. Any disputes shall be resolved by binding arbitration.",

    "Both parties acknowledge that any breach of this Agreement may cause irreparable harm "
    "for which monetary damages would be an inadequate remedy.",
]

REPORT_BODY = [
    "Q2 Financial Performance Report — Internal Use Only",

    "1. <b>Revenue Summary.</b> Total consolidated revenue for Q2 reached ₹4.2 crore, "
    "representing a 18% year-over-year increase driven primarily by growth in recurring "
    "SaaS subscriptions and professional services.",

    "2. <b>Operating Expenses.</b> Total operating expenses were ₹2.8 crore, with the "
    "largest components being personnel costs (62%), cloud infrastructure (21%), and "
    "sales & marketing (17%).",

    "3. <b>EBITDA.</b> Earnings before interest, taxes, depreciation and amortisation "
    "stood at ₹1.1 crore, a margin of 26.2% compared to 19.8% in Q2 of the prior year.",

    "4. <b>Outlook.</b> Management reaffirms full-year guidance of ₹17–18 crore in revenue "
    "and anticipates EBITDA margin expansion of 200–300 basis points driven by operating "
    "leverage and improved gross retention.",

    "<i>This document is classified Confidential. Unauthorised disclosure is prohibited.</i>",
]

AGREEMENT_BODY = [
    "Service Level Agreement — Pending Execution",

    "1. <b>Services.</b> The Provider agrees to deliver software development and technical "
    "advisory services as detailed in Schedule A (attached). Delivery timelines are subject "
    "to mutual written approval.",

    "2. <b>Payment Terms.</b> Fees are payable within 30 days of invoice. Late payments "
    "shall accrue interest at 1.5% per month. All amounts are exclusive of applicable taxes.",

    "3. <b>Intellectual Property.</b> All work product created specifically for the Client "
    "under this Agreement shall be deemed work-made-for-hire and shall vest in the Client "
    "upon receipt of full payment.",

    "4. <b>Limitation of Liability.</b> In no event shall either party's liability exceed "
    "the total fees paid in the preceding twelve months.",

    "<b>Status: Awaiting authorised signature before this agreement takes legal effect.</b>",
]


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n== DocVault Demo Setup ==================================")
    print("Logging in...")
    token = login()

    # ── 1. VERIFIED document ─────────────────────────────────────────────────
    print("\n[1/3] Creating VERIFIED document...")
    pdf1 = make_pdf_bytes("Non-Disclosure Agreement", CONTRACT_BODY)
    doc1 = upload(token, "contract_verified.pdf", pdf1, USERNAME, "Legal",
                  "Demonstration of a fully verified, tamper-evident contract.")
    sign(token, doc1["id"])
    verify(token, doc1["id"], pdf1)
    print(f"  OK  contract_verified.pdf  -> status should be VERIFIED")

    # ── 2. TAMPERED document ──────────────────────────────────────────────────
    print("\n[2/3] Creating TAMPERED document...")
    pdf2_original = make_pdf_bytes("Q2 Financial Report", REPORT_BODY)
    doc2 = upload(token, "report_tampered.pdf", pdf2_original, USERNAME, "Confidential",
                  "Financial report -- will be tampered post-signing for demonstration.")
    sign(token, doc2["id"])

    # Tamper the bytes: flip a range of bytes in the middle of the PDF body
    pdf2_tampered = bytearray(pdf2_original)
    mid = len(pdf2_tampered) // 2
    for i in range(mid, mid + 80):
        pdf2_tampered[i] = pdf2_tampered[i] ^ 0xFF  # bit-flip
    pdf2_tampered = bytes(pdf2_tampered)

    verify(token, doc2["id"], pdf2_tampered)
    print(f"  OK  report_tampered.pdf    -> status should be TAMPERED")

    # ── 3. AWAITING SIGNATURE document ───────────────────────────────────────
    print("\n[3/3] Creating document awaiting signature...")
    pdf3 = make_pdf_bytes("Service Level Agreement", AGREEMENT_BODY)
    doc3 = upload(token, "agreement_to_sign.pdf", pdf3, USERNAME, "Legal",
                  "SLA pending authorised signature.")
    print(f"  OK  agreement_to_sign.pdf  -> status should be UPLOADED (unsigned)")

    print("\n== Done =================================================")
    print(f"  Doc 1 (VERIFIED) : /documents/{doc1['id']}")
    print(f"  Doc 2 (TAMPERED) : /documents/{doc2['id']}")
    print(f"  Doc 3 (UNSIGNED) : /documents/{doc3['id']}")
    print()

if __name__ == "__main__":
    main()
