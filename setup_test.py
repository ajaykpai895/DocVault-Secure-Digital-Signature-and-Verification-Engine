import os
import base64
from app.database import Base, engine, SessionLocal
from app.models.user import User
from app.models.document import Document
from app.models.signature import SignatureRecord
from app.crypto.key_manager import generate_key_pair

# 1. Reset Database
for db_file in ["docvault.db", "test_docvault.db"]:
    if os.path.exists(db_file):
        os.remove(db_file)
        
Base.metadata.create_all(bind=engine)

# 2. Create Dummy PDF
minimal_pdf = b"""
JVBERi0xLjQKMSAwIG9iago8PC9UeXBlIC9DYXRhbG9nIC9QYWdlcyAyIDAgUj4+CmVuZG9iagoyIDAgb2JqCjw8L1R5cGUgL1BhZ2VzIC9LaWRzIFszIDAgUl0gL0NvdW50IDE+PgplbmRvYmoKMyAwIG9iago8PC9UeXBlIC9QYWdlIC9QYXJlbnQgMiAwIFIgL01lZGlhQm94IFswIDAgNjEyIDc5Ml0+PgplbmRvYmoKeHJlZgowIDQKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwNTIgMDAwMDAgbiAKMDAwMDAwMDEwMSAwMDAwMCBuIAp0cmFpbGVyCjw8L1NpemUgNCAvUm9vdCAxIDAgUj4+CnN0YXJ0eHJlZgoxNzMKJSVFT0YK
"""
with open("dummy.pdf", "wb") as f:
    f.write(base64.b64decode(minimal_pdf))

# 3. Create Test User
db = SessionLocal()
priv_pem, pub_pem = generate_key_pair(b"mypassword")
test_user = User(
    username="testuser",
    email="test@example.com",
    hashed_password="hashed_placeholder_for_now",
    public_key=pub_pem.decode('utf-8'),
    private_key_encrypted=priv_pem.decode('utf-8')
)
db.add(test_user)
db.commit()
db.refresh(test_user)

with open("test_user.txt", "w") as f:
    f.write(test_user.id)
