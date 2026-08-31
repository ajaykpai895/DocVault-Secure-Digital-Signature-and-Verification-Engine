import pytest
import hashlib
from app.crypto.key_manager import generate_key_pair, load_private_key, load_public_key
from app.crypto.signature_engine import sign_hash, verify_signature

@pytest.fixture
def key_pair_data():
    password = b"super_secret_password"
    priv_pem, pub_pem = generate_key_pair(password)
    return priv_pem, pub_pem, password

@pytest.fixture
def keys(key_pair_data):
    priv_pem, pub_pem, password = key_pair_data
    priv_key = load_private_key(priv_pem, password)
    pub_key = load_public_key(pub_pem)
    return priv_key, pub_key

def test_generate_and_load_keys(key_pair_data):
    priv_pem, pub_pem, password = key_pair_data
    priv_key = load_private_key(priv_pem, password)
    pub_key = load_public_key(pub_pem)
    assert priv_key is not None
    assert pub_key is not None

def test_load_private_key_wrong_password(key_pair_data):
    priv_pem, _, _ = key_pair_data
    with pytest.raises(ValueError):
        load_private_key(priv_pem, b"wrong_password")

def test_valid_signature(keys):
    priv_key, pub_key = keys
    # Dummy SHA-512 hash
    doc_hash = hashlib.sha512(b"DocVault test doc").hexdigest()
    
    signature = sign_hash(priv_key, doc_hash)
    assert verify_signature(pub_key, doc_hash, signature) is True

def test_invalid_signature_tampered_doc(keys):
    priv_key, pub_key = keys
    original_hash = hashlib.sha512(b"DocVault test doc").hexdigest()
    tampered_hash = hashlib.sha512(b"DocVault test doc tampered").hexdigest()
    
    signature = sign_hash(priv_key, original_hash)
    
    # Verify with the tampered hash
    assert verify_signature(pub_key, tampered_hash, signature) is False

def test_invalid_signature_wrong_public_key(keys):
    priv_key, _ = keys
    
    # Generate a second key pair
    _, pub_pem2 = generate_key_pair(b"another_password")
    wrong_pub_key = load_public_key(pub_pem2)
    
    doc_hash = hashlib.sha512(b"DocVault test doc").hexdigest()
    signature = sign_hash(priv_key, doc_hash)
    
    # Verify with the wrong public key
    assert verify_signature(wrong_pub_key, doc_hash, signature) is False
