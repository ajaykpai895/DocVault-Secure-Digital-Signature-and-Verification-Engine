import os
import tempfile
import hashlib
import pytest
from app.crypto.hash_engine import compute_file_hash, compute_bytes_hash, verify_hash_unchanged

@pytest.fixture
def temp_test_file():
    """Creates a temporary file with known content for testing."""
    fd, path = tempfile.mkstemp()
    with os.fdopen(fd, 'wb') as f:
        f.write(b"DocVault secure testing data.")
    yield path
    os.remove(path)

def test_compute_bytes_hash():
    data = b"DocVault secure testing data."
    expected_hash = hashlib.sha512(data).hexdigest()
    assert compute_bytes_hash(data) == expected_hash

def test_compute_file_hash(temp_test_file):
    data = b"DocVault secure testing data."
    expected_hash = hashlib.sha512(data).hexdigest()
    assert compute_file_hash(temp_test_file) == expected_hash

def test_verify_hash_unchanged_valid(temp_test_file):
    expected_hash = compute_file_hash(temp_test_file)
    assert verify_hash_unchanged(temp_test_file, expected_hash) is True

def test_verify_hash_unchanged_tampered(temp_test_file):
    expected_hash = compute_file_hash(temp_test_file)
    
    # Tamper with the file by modifying a byte
    with open(temp_test_file, 'r+b') as f:
        f.seek(0)
        f.write(b"X")
        
    assert verify_hash_unchanged(temp_test_file, expected_hash) is False
