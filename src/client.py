import random
import time
import os
import fcntl
import struct
import subprocess
import asyncio
from scapy.all import IP
from wrap import wrap_packet
from config import load_client_config
from crypto import encrypt, decrypt, hash

HOST, PORT, MODE, PASSWORD = load_client_config()

async def handle_connection(reader, writer):
    print(f"Connected to server at: {HOST}:{PORT}")

    global PASSWORD
    print(PASSWORD)
    PASSWORD = str(PASSWORD) + "\n"

    writer.write(PASSWORD.encode("utf-8"))
    await writer.drain()
    
    try:
        K = await key_exchange(reader,writer)
        K = hash(K)
        while True:
                await send_packets(reader, writer,K)
    except ConnectionResetError:
        print(f"Connection lost (ConnectionResetError)")
    except Exception as e:
         print(f"Unexpected error: {e}")
    finally:
        print("Closing connection...")
        writer.close()
        await writer.wait_closed()

'''
async def pingTest(reader, writer):
    start = time.perf_counter()
    writer.write("Ping!".encode("utf-8"))
    await writer.drain()

    pong = await reader.read(1024)
    pong = pong.decode("utf-8")

    if pong:
        end = time.perf_counter()
        ping = int((end - start) * 1000)
        print(f"[DEBUG CLIENT] Modtog: {pong}. Din ping er {ping} ms")
    else:
        print("[DEBUG CLIENT FEJL] Kunne ikke modtage pong!")
'''
async def key_exchange(reader, writer):
    print("Starting key exchange...")
    sentence = "Key request"
    writer.write(sentence.encode("utf-8"))
    await writer.drain()
    
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

async def send_packets(reader, writer, K):
    print("Setting up TUN interface locally...")
    TUNSETIFF = 0x400454ca
    IFF_TUN = 0x0001
    IFF_NO_PI = 0x1000
    REAL_INTERFACE = "eth0"
    REAL_GATEWAY = "192.168.1.1"

    tun = os.open("/dev/net/tun", os.O_RDWR)
    ifr = struct.pack("16sH", b"tun0", IFF_TUN | IFF_NO_PI)
    fcntl.ioctl(tun, TUNSETIFF, ifr)

    print("Configuring IP and routing on client...")
    subprocess.run(["ip", "addr", "add", "10.0.0.2/24", "dev", "tun0"], check=True)
    subprocess.run(["ip", "link", "set", "tun0", "up"], check=True)
    time.sleep(1) 

    # BRUG FORSKELLIGE LINJER AN PÅ OM DET ER GLOBAL ELLER LOKAL:
    if MODE == "local":
        subprocess.run(["ip", "route", "replace", HOST, "dev", REAL_INTERFACE], check=True) # Lokal
    elif MODE == "global":   
        subprocess.run(["ip", "route", "replace", HOST, "via", REAL_GATEWAY, "dev", REAL_INTERFACE], check=True) # Global

    subprocess.run(["sudo", "sysctl", "-w", "net.ipv6.conf.all.disable_ipv6=1"], check=True)

    subprocess.run(["ip", "route", "replace", "0.0.0.0/1", "dev", "tun0"], check=True)
    subprocess.run(["ip", "route", "replace", "128.0.0.0/1", "dev", "tun0"], check=True)

    loop = asyncio.get_running_loop()

    async def read_tun():
        print("Reading from TUN interface...")

        # Client needs to send an initalizing unencrypted packet to server, to tell that client is ready
        init_packet = wrap_packet(await loop.run_in_executor(None, os.read, tun, 2048))
        writer.write(init_packet)
        await writer.drain()

        while True:
            try:
                packet = await loop.run_in_executor(None, os.read, tun, 2048)
                wrapped = encrypt(K, packet)
                wrapped = wrap_packet(wrapped)
                writer.write(wrapped)
                await writer.drain()
            except Exception as e:
                print(f"Error: {e}")
                break
    
    async def write_tun():
        while True:
            try:
                packet = await unwrap_packet(reader,K)
                if not packet:
                    break
                await loop.run_in_executor(None, os.write, tun, packet)
                try: 
                    ip = IP(packet[:20]) 
                    print(f"Packet-info: {ip.src} -> {ip.dst}")
                except: 
                    pass
            except Exception as e:
                break

    try:
        await asyncio.gather(read_tun(), write_tun())
    except asyncio.CancelledError:
        print("Closing TUN interface...")

async def unwrap_packet(reader,K):
    raw_len = await reader.readexactly(4)
    size = struct.unpack("!I", raw_len)[0]

    packet = await reader.readexactly(size)
    packet = decrypt(K,packet)
    return packet

async def main():
    print("Starting main...")
    reader, writer = await asyncio.open_connection(HOST, PORT)
    await handle_connection(reader, writer)

if __name__ == "__main__":
    asyncio.run(main())