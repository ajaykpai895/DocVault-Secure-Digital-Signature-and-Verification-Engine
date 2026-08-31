import hashlib
import hmac

def compute_file_hash(file_path: str) -> str:
    """
    Computes the SHA-512 hash of a file, reading it in chunks 
    to prevent high memory usage.
    """
    sha512_hash = hashlib.sha512()
    with open(file_path, "rb") as f:
        # Read and update hash in chunks of 64K
        for byte_block in iter(lambda: f.read(65536), b""):
            sha512_hash.update(byte_block)
    return sha512_hash.hexdigest()

def compute_bytes_hash(data: bytes) -> str:
    """
    Computes the SHA-512 hash of in-memory byte content.
    """
    sha512_hash = hashlib.sha512()
    sha512_hash.update(data)
    return sha512_hash.hexdigest()

def verify_hash_unchanged(file_path: str, expected_hash: str) -> bool:
    """
    Recomputes the hash of a file and compares it to the expected hash
    using a constant-time comparison to prevent timing attacks.
    """
    current_hash = compute_file_hash(file_path)
    return hmac.compare_digest(current_hash, expected_hash)
