from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import time
import os


def cut_key(key):
    if key.bit_length() > 256:
        key = key >> key.bit_length() - 256
    return key

def encrypt(key,data):

    key = key.encode()

    aesgcm = AESGCM(key)

    nonce = os.urandom(12) 
    ciphertext = aesgcm.encrypt(nonce, data, None)

    return nonce + ciphertext

def decrypt(key,ciphertext):
    nonce = ciphertext[:12]
    encrypted_payload = ciphertext[12:]

    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, encrypted_payload, None)