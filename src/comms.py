import random
from Crypto.Util import number
from .crypto import decrypt
import struct

# Function for servers side of handshake
async def server_handshake(reader, writer, addr):
    print(f"[DEBUG SERVER] Starter key exchange med {addr}...")
    # Generating prime number for use in encryption
    q = number.getPrime(2048)
    # Make sure that prime number is "strong"
    p = 2 * q + 1

    # Generate random valid "generator" number
    g = random.randrange(2, p-1)
    while pow(g,2,p) == 1 and pow(g,q,p) == 1:
        g = random.randrange(2, p-1)


    # Generate random private key and calculate public key
    a = random.randint(50, 200)
    A = pow(g,a,p)

    # Send the prime and generator to the client as a string
    p_send = str(p)+"\n"
    g = str(g)+"\n"

    writer.write(p_send.encode("utf-8"))
    await writer.drain()

    writer.write(g.encode("utf-8"))
    await writer.drain()

    # Recieve clients public key
    B_bytes = await reader.readline()
    if not B_bytes:
        return 
        
    # Decode clients public key into usable number
    B = B_bytes.decode("utf-8")

    # Send server public key to client
    A = str(A) + "\n"
    writer.write(A.encode("utf-8"))
    await writer.drain()

    # Calculate shared key from clients public key, servers private key and prime
    K = pow(int(B), a, p)
    print(f"Key exchange was done succesfuly with {addr}")

    return K

# Function for clients side of handshake
async def client_handshake(reader,writer):
    print("Starting key exchange...")
    
    # Awaits prime and generator from server
    p_bytes = await reader.readline()
    p = p_bytes.decode("utf-8")
    g_bytes = await reader.readline()
    g = g_bytes.decode("utf-8")

    p = int(p)
    g = int(g)

    # Generate client private key and calculate public client key
    b = random.randint(50,200)
    B = pow(g, b, p)

    # Send client public key to server
    B = str(B) + "\n"
    writer.write(B.encode("utf-8"))
    await writer.drain()
    
    # Await server public key from server
    A_bytes = await reader.readline()
    A = A_bytes.decode("utf-8")
    A = int(A)
    
    # Calculate shared key
    K = pow(A, b, p)
    
    print("Key exchange was a sucess")
    return K

async def unwrap_packet(reader,K):
    raw_len = await reader.readexactly(4)
    size = struct.unpack("!I", raw_len)[0]

    packet = await reader.readexactly(size)
    packet = decrypt(packet,K)
    return packet

async def wrap_packet(packet_bytes):
    length = len(packet_bytes)
    return struct.pack("!I", length) + packet_bytes
