import pytest
import json
import base64
from datetime import datetime, timezone
from app.crypto.metadata_cipher import encrypt_metadata, decrypt_metadata

@pytest.fixture
def master_key():
    return b"123456789012345678901234" # 24 bytes for 3DES

@pytest.fixture
def sample_metadata():
    return json.dumps({
        "owner_name": "Alice Smith",
        "document_id": "doc-555-abc",
        "classification": "Confidential",
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "Legal Agreement"
    })

def test_metadata_round_trip(sample_metadata, master_key):
    encrypted = encrypt_metadata(sample_metadata, master_key)
    decrypted = decrypt_metadata(encrypted, master_key)
    assert decrypted == sample_metadata

def test_different_ivs_for_identical_plaintext(sample_metadata, master_key):
    encrypted1 = encrypt_metadata(sample_metadata, master_key)
    encrypted2 = encrypt_metadata(sample_metadata, master_key)
    
    assert encrypted1 != encrypted2
    
    # We can also decode and check that the first 8 bytes (IV) differ
    data1 = base64.b64decode(encrypted1)
    data2 = base64.b64decode(encrypted2)
    assert data1[:8] != data2[:8]

def test_decrypt_with_wrong_key(sample_metadata, master_key):
    encrypted = encrypt_metadata(sample_metadata, master_key)
    wrong_key = b"wrong_key_12345678901234"
    
    with pytest.raises(ValueError):
        # The padding or decryption will fail with a wrong key
        decrypt_metadata(encrypted, wrong_key)
