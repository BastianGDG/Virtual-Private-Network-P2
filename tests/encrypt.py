from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import time
import os

acc = 0

for i in range(1000):
    key = AESGCM.generate_key(bit_length=256)
    aesgcm = AESGCM(key)

    data = b"hejsa det her er secret stuff"

    start = time.perf_counter()
    for i in range(1000):
        nonce = os.urandom(12) 
        ciphertext = aesgcm.encrypt(nonce, data, None)
    end = time.perf_counter()

    timer = end - start
    
    acc = acc + timer

print(f"Det tog: {acc/100} sekunder")