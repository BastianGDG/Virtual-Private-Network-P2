from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import hashlib


def hash(key):
    # Try to convert key to binary, if it fails it's likely a string
    try:
        # Convert a numeral key to binary
        length = (key.bit_length() + 7) // 8
        key = key.to_bytes(length, "big")
    except:
        # Convert a string key to binary
        key = key.encode()

    # Hash the key
    key = hashlib.sha256(key).digest()
    return key

def encrypt(data,K):
    try:
        # Initialize encryptionobject
        aesgcm = AESGCM(K)
        # Generate a random nonce
        nonce = os.urandom(12) 
        # encrypt the data
        ciphertext = aesgcm.encrypt(nonce, data, None)
        
        # return nonce and ciphertext together
        return nonce + ciphertext
    
    except Exception as e:
        print(f"Error encrypting: {e}")
        return None

def decrypt(ciphertext,K):
    try:
        # Seperate nonce and ciphertext from recieved packet
        nonce = ciphertext[:12]
        encrypted_payload = ciphertext[12:]

        aesgcm = AESGCM(K)

        # Return decrypted ciphertext
        return aesgcm.decrypt(nonce, encrypted_payload, None)
    except Exception as e:
        print(f"Error decrypting: {e}")
        return None
