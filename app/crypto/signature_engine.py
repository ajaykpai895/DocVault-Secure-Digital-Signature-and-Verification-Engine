from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
from cryptography.exceptions import InvalidSignature

def sign_hash(private_key, document_hash_hex: str) -> bytes:
    """
    Signs a document hash using ECDSA.
    Since the input is already a SHA-512 hash (hex), we convert it to bytes
    and use Prehashed(hashes.SHA512()) to sign it directly.
    """
    hash_bytes = bytes.fromhex(document_hash_hex)
    
    signature = private_key.sign(
        hash_bytes,
        ec.ECDSA(Prehashed(hashes.SHA512()))
    )
    return signature

def verify_signature(public_key, document_hash_hex: str, signature: bytes) -> bool:
    """
    Verifies the ECDSA signature of a document hash.
    Returns True if valid, False otherwise.
    """
    hash_bytes = bytes.fromhex(document_hash_hex)
    
    try:
        public_key.verify(
            signature,
            hash_bytes,
            ec.ECDSA(Prehashed(hashes.SHA512()))
        )
        return True
    except InvalidSignature:
        return False
