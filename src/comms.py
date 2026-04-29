import random
from Crypto.Util import number

async def server_handshake(reader, writer, addr):
    print(f"[DEBUG SERVER] Starter key exchange med {addr}...")
    q = number.getPrime(2048)
    p = 2 * q + 1
    g = random.randrange(2, p-1)
    while pow(g,2,p) == 1 and pow(g,q,p) == 1:
        g = random.randrange(2, p-1)

    a = random.randint(50, 200)
    A = pow(g,a,p)

    p_send = str(p)+"\n"
    g = str(g)+"\n"

    writer.write(p_send.encode("utf-8"))
    await writer.drain()

    writer.write(g.encode("utf-8"))
    await writer.drain()

    B_bytes = await reader.readline()
    if not B_bytes:
        return 
        
    B = B_bytes.decode("utf-8")

    A = str(A) + "\n"
    writer.write(A.encode("utf-8"))
    await writer.drain()

    K = pow(int(B), a, p)
    print(f"Key exchange was done succesfuly with {addr}")

    return K

async def client_handshake(reader,writer):
    print("Starting key exchange...")
    
    p_bytes = await reader.readline()
    p = p_bytes.decode("utf-8")
    g_bytes = await reader.readline()
    g = g_bytes.decode("utf-8")

    p = int(p)
    g = int(g)
    b = random.randint(50,200)
    B = pow(g, b, p)

    B = str(B) + "\n"

    writer.write(B.encode("utf-8"))
    await writer.drain()
    
    A_bytes = await reader.readline()
    A = A_bytes.decode("utf-8")
    A = int(A)

    K = pow(A, b, p)
    
    print("Key exchange was a sucess")
    return K
