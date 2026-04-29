import random
from Crypto.Util import number
import asyncio
import os
import struct
import fcntl
from scapy.all import IP
import subprocess
from wrap import wrap_packet
from crypto import encrypt, decrypt, hash
from config import load_server_config
from server.peer import create_peer, flush_table, lookup
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from src.setup import create_tun_interface, configure_server_routing

# Server configuration
HOST = "0.0.0.0"
PORT = 6789

# Load server password from input or config file
PASSWORD = load_server_config()

# If password was inputted, hash it, otherwise PASSWORD will be None and the server will not require authentication

if PASSWORD:
    PASSWORD = hash(PASSWORD)

# Global variable to keep track of connected clients, this is used to give unique IDs to clients as they connect
CLIENT_COUNT = 0

CLIENTS = {}

# Set up TUN interface and network configuration
print("[DEBUG SERVER] Sætter TUN interface op...")
TUN = create_tun_interface()

print("[DEBUG SERVER] TUN interface oprettet: tun0")

cmd = ["ip", "route", "show", "default"]
result = subprocess.check_output(cmd).decode('utf-8')
    
REAL_INTERFACE = result.split()[4]

# Configure IP and routing on server
configure_server_routing(REAL_INTERFACE)
print("[DEBUG SERVER] Netværkskonfiguration og iptables regler anvendt.")

# Flush peer table on server start, to make sure no old peers are present
flush_table()

async def socket_to_tun(reader,K,aesgcm):
    while True:
        try:
            packet = await unwrap_packet(reader,K,aesgcm)
            Ip = IP(packet[:20])
            Ip = Ip.src
            print(f"Ip: {Ip}, key: {K.hex()}")
            if not packet:
                break
            os.write(TUN, packet)
        except asyncio.IncompleteReadError as e:
            print(f"linje 44 {e}")
            break
        except Exception as e:
            print(f"linje 47 {e}")
            break

async def tun_to_socket(writer,K,aesgcm):
    loop = asyncio.get_running_loop()
    while True:
        try:
            packet = await loop.run_in_executor(None, os.read, TUN, 2048)
            Ip = IP(packet[:20])
            dest = Ip.dst 

            ID = dest.split(".")
            ID = ID[-1]

            peer = lookup(ID)
            Ip = getattr(peer,"IP")
            writer = CLIENTS.get(Ip)

            K = getattr(peer,"key")
            K = bytes.fromhex(K)

            wrapped = encrypt(packet,aesgcm)
            wrapped = wrap_packet(wrapped)
            writer.write(wrapped)
        except Exception as e:
            print(f"linje 60 {e}")

async def handle_client(reader, writer):
    addr = writer.get_extra_info("peername")
    print(f"\n[DEBUG SERVER] New client connected: {addr}")
    
    input_password = await reader.readline()
    input_password = input_password.decode("utf-8", errors="ignore")
    input_password = input_password.removesuffix("\n")
    input_password = hash(input_password)

    try:
        if input_password == PASSWORD:
            K = await key_exchange(reader, writer, addr)
            K = hash(K)

            aesgcm = AESGCM(K)

            K = K.hex()

            global CLIENT_COUNT
            CLIENT_COUNT += 1

            ip = addr[0]

            CLIENTS[ip] = writer

            peer = create_peer(str(CLIENT_COUNT), addr[0], K)
            K = bytes.fromhex(K)

            Virtual_IP = getattr(peer,"Virtual_IP")
            Virtual_IP = Virtual_IP + "\n"
            writer.write(Virtual_IP.encode("utf-8"))
            await writer.drain()

            while True:
                data = await reader.read(2048)
                if not data:
                    print("[DEBUG SERVER] handle_client: Modtog 0 bytes, client har lukket forbindelsen.")
                    break
                    
                elif len(data) > 4:
                    length = struct.unpack("!I", data[:4])[0]

                    first_packet = data[4:4+length]
                    os.write(TUN, first_packet)

                    await asyncio.gather(
                        socket_to_tun(reader,K,aesgcm),
                        tun_to_socket(writer,K,aesgcm)
                    )
                    print("[DEBUG SERVER] handle_client: TUN loops er afsluttet.")
                    break 
                else:
                    print(f"[DEBUG SERVER] handle_client: Modtog meget kort/ukendt data: {data}")
                
    except Exception as e:
        print(f"[DEBUG SERVER FEJL] i handle_client: {e}")
    finally:
        print(f"[DEBUG SERVER] Lukker forbindelsen til {addr}")
        writer.close()
        await writer.wait_closed()

async def key_exchange(reader, writer, addr):
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

async def unwrap_packet(reader,K,aesgcm):
    raw_len = await reader.readexactly(4)
    size = struct.unpack("!I", raw_len)[0]

    packet = await reader.readexactly(size)
    packet = decrypt(packet,aesgcm)
    return packet

async def main():
    server = await asyncio.start_server(handle_client, HOST, PORT)
    addr = server.sockets[0].getsockname()
    print(f"[DEBUG SERVER] Async Server is ready and listening on {addr}...")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())