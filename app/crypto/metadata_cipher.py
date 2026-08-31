import os
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

# Note: 3DES (Triple DES / DES-EDE3) is used here only because it was 
# specified as a project requirement. For new systems, AES-256-GCM 
# would be the modern recommended choice.

def encrypt_metadata(plaintext_json: str, key: bytes) -> str:
    """
    Encrypts a JSON metadata string using Triple DES (3DES) in CBC mode.
    Prepends an 8-byte random IV to the ciphertext and returns it as a base64 string.
    """
    iv = os.urandom(8)
    
    cipher = Cipher(algorithms.TripleDES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    
    padder = padding.PKCS7(algorithms.TripleDES.block_size).padder()
    padded_data = padder.update(plaintext_json.encode('utf-8')) + padder.finalize()
    
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()
    
    # Store IV alongside the ciphertext: IV + ciphertext
    combined_data = iv + ciphertext
    return base64.b64encode(combined_data).decode('utf-8')

def decrypt_metadata(ciphertext_b64: str, key: bytes) -> str:
    """
    Decrypts a base64-encoded metadata string containing the IV and ciphertext.
    Returns the original JSON string.
    """
    combined_data = base64.b64decode(ciphertext_b64)
    
    if len(combined_data) < 8:
        raise ValueError("Invalid ciphertext length")
        
    iv = combined_data[:8]
    ciphertext = combined_data[8:]
    
    cipher = Cipher(algorithms.TripleDES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    
    padded_data = decryptor.update(ciphertext) + decryptor.finalize()
    
    unpadder = padding.PKCS7(algorithms.TripleDES.block_size).unpadder()
    plaintext_bytes = unpadder.update(padded_data) + unpadder.finalize()
    
    return plaintext_bytes.decode('utf-8')
