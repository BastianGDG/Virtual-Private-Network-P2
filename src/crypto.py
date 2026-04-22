from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import hashlib


def hash(key):
    try:
        length = (key.bit_length() + 7) // 8
        key = key.to_bytes(length, "big")
    except:
        key = key.encode()

    key = hashlib.sha256(key).digest()
    
    return key

def encrypt(key,data):
    try:
        aesgcm = AESGCM(key)

        nonce = os.urandom(12) 
        ciphertext = aesgcm.encrypt(nonce, data, None)
        
        return nonce + ciphertext
    except Exception as e:
        print(e)
        return None

def decrypt(key,ciphertext):
    nonce = ciphertext[:12]
    encrypted_payload = ciphertext[12:]

    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, encrypted_payload, None)
