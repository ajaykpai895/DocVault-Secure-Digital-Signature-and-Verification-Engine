import json
import sys
import requests

BASE = "http://127.0.0.1:8000"
PASSWORD = "mypassword123"
USERNAME = "testuser_e2e"
EMAIL = "e2e@example.com"

def check(label, response, expected_status=200):
    ok = response.status_code == expected_status
    mark = "OK" if ok else "FAIL"
    print(f"  [{mark}] [{response.status_code}] {label}")
    if not ok:
        print(f"       Body: {response.text[:300]}")
    return ok


print("=" * 60)
print("  DocVault v2.0 - End-to-End Test")
print("=" * 60)

# 1. Register
print("\n--- REGISTER ---")
r = requests.post(f"{BASE}/auth/register", json={
    "username": USERNAME,
    "email": EMAIL,
    "password": PASSWORD,
    "role": "OWNER",
})
if r.status_code == 409:
    print("  INFO: User already exists - skipping registration.")
elif not check("Register new user", r, 201):
    sys.exit(1)

# 2. Login
print("\n--- LOGIN ---")
r = requests.post(f"{BASE}/auth/login", data={"username": USERNAME, "password": PASSWORD})
if not check("Login and get JWT token", r, 200):
    sys.exit(1)
token = r.json()["access_token"]
user_id = r.json()["user_id"]
headers = {"Authorization": f"Bearer {token}"}
print(f"  INFO: User ID: {user_id}")
print(f"  INFO: Token  : {token[:30]}...")

# 3. Upload
print("\n--- UPLOAD DOCUMENT ---")
metadata = {"owner_name": "Alice Doe", "purpose": "Legal Contract", "classification": "CONFIDENTIAL"}
r = requests.post(
    f"{BASE}/documents/upload",
    headers=headers,
    data={"metadata_json": json.dumps(metadata)},
    files={"file": ("dummy.pdf", open("dummy.pdf", "rb"), "application/pdf")},
)
if not check("Upload PDF document", r, 200):
    sys.exit(1)
doc_id = r.json()["id"]
sha = r.json()["sha512_hash"]
print(f"  INFO: Document ID : {doc_id}")
print(f"  INFO: SHA-512     : {sha[:32]}...")

# 4. Sign
print("\n--- SIGN DOCUMENT ---")
r = requests.post(
    f"{BASE}/documents/{doc_id}/sign",
    headers=headers,
    data={"private_key_password": PASSWORD},
)
if not check("Sign document with ECDSA", r, 200):
    sys.exit(1)
sig_id = r.json()["id"]
print(f"  INFO: Signature ID: {sig_id}")

# 5. Verify (original file)
print("\n--- VERIFY DOCUMENT (original file) ---")
r = requests.post(
    f"{BASE}/documents/{doc_id}/verify",
    headers=headers,
    files={"file": ("dummy.pdf", open("dummy.pdf", "rb"), "application/pdf")},
)
check("Verify original file -> expect VALID", r, 200)
if r.status_code == 200:
    result = r.json()
    status_icon = "PASS" if result["overall_status"] == "VALID" else "WARN"
    print(f"  [{status_icon}] overall_status = {result['overall_status']}")
    print(f"      hash_match={result['hash_match']}  signature_valid={result['signature_valid']}")

# 6. Audit Trail
print("\n--- AUDIT TRAIL ---")
r = requests.get(f"{BASE}/documents/{doc_id}/audit", headers=headers)
check("Fetch audit trail", r, 200)
if r.status_code == 200:
    events = r.json()
    print(f"  INFO: {len(events)} audit event(s) recorded:")
    for e in events:
        print(f"    * [{e['action']}] {e['status']} - {str(e.get('detail',''))[:60]}")

# 7. QR Quick-Verify
print("\n--- QR QUICK-VERIFY (no file upload) ---")
r = requests.get(f"{BASE}/documents/{doc_id}/verify-qr")
check("QR quick-verify endpoint (public)", r, 200)
if r.status_code == 200:
    print(f"  INFO: {r.json().get('message', '')}")

print("\n" + "=" * 60)
print("  All tests complete!")
print("=" * 60)
