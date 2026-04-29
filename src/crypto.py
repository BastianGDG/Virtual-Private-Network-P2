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

def encrypt(data,K):
    try:

        aesgcm = AESGCM(K)
        #Generate a random nonce
        nonce = os.urandom(12) 
        #encrypts the data
        ciphertext = aesgcm.encrypt(nonce, data, None)
        
        # returns nonce and ciphertext together
        return nonce + ciphertext
    except Exception as e:
        print(f"Error encrypting: {e}")
        return None

def decrypt(ciphertext,K):
    try:
        # Seperates nonce and ciphertext from recieved packet
        nonce = ciphertext[:12]
        encrypted_payload = ciphertext[12:]

        aesgcm = AESGCM(K)
        return aesgcm.decrypt(nonce, encrypted_payload, None)
    except Exception as e:
        print(f"Error decrypting: {e}")
        return None
