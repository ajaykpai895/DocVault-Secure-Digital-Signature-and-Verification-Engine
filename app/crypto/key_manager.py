from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

def generate_key_pair(password: bytes) -> tuple[bytes, bytes]:
    """
    Generates a new ECDSA key pair using the SECP384R1 curve.
    Returns the PEM-encoded private and public keys.
    The private key is encrypted with the provided password.
    """
    private_key = ec.generate_private_key(ec.SECP384R1())
    
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(password)
    )
    
    public_key = private_key.public_key()
    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    return private_key_pem, public_key_pem

def load_private_key(pem_data: bytes, password: bytes):
    """
    Loads an encrypted private key from PEM bytes.
    Raises ValueError if the password is wrong or key is invalid.
    """
    return serialization.load_pem_private_key(
        pem_data,
        password=password
    )

def load_public_key(pem_data: bytes):
    """
    Loads a public key from PEM bytes.
    """
    return serialization.load_pem_public_key(pem_data)
