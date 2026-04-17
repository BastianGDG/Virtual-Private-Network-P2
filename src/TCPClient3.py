import socket
import random
import time
import os
import fcntl
import struct
import subprocess
import asyncio
from scapy.all import IP
from wrapunwrap import wrap_packet

# HUSK AT TJEKKE DENNE IP IGEN
HOST = "192.168.1.170" 
PORT = 6789

async def handle_connection(reader, writer):
    print(f"[DEBUG CLIENT] Forbundet til server på {HOST}:{PORT}")

    try:
        while True:
            print("\n1: Ping test")
            print("2: Key exchange")
            print("3: Create TUN interface (Start VPN)")
            print("4: Exit")
            choice = await asyncio.to_thread(input, "Select a choice: ")
            
            try:
                choice = int(choice)
            except ValueError:
                print("[DEBUG CLIENT] Ugyldigt valg, indtast et tal.")
                continue
    
            if choice == 1:
                await pingTest(reader, writer)
            elif choice == 2:
                await keyExchange(reader, writer)
            elif choice == 3:
                print("[DEBUG CLIENT] Valg 3: Starter VPN tunneling...")
                await send_packets(reader, writer)
            elif choice == 4:
                break
            else:
                print("[DEBUG CLIENT] Forkert valg")
      
    except ConnectionResetError:
        print(f"[DEBUG CLIENT FEJL] Connection lost (ConnectionResetError)")
    except Exception as e:
         print(f"[DEBUG CLIENT FEJL] Uventet fejl: {e}")
    finally:
        print("[DEBUG CLIENT] Lukker writer...")
        writer.close()
        await writer.wait_closed()

async def pingTest(reader, writer):
    print("[DEBUG CLIENT] Starter ping test...")
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

async def keyExchange(reader, writer):
    print("[DEBUG CLIENT] Starter key exchange...")
    sentence = "Key request"
    writer.write(sentence.encode("utf-8"))
    await writer.drain()
    
    p_bytes = await reader.read(1024)
    p = p_bytes.decode("utf-8")
    g_bytes = await reader.read(1024)
    g = g_bytes.decode("utf-8")

    p = int(p)
    g = int(g)
    b = random.randint(1,100)
    B = pow(g, b, p)
    writer.write(str(B).encode("utf-8"))
    await writer.drain()
    
    A_bytes = await reader.read(1024)
    A = A_bytes.decode("utf-8")
    A = int(A)

    K = pow(A, b, p)
    print(f"[DEBUG CLIENT] Key exchange succes! Shared Key: {K}")

async def send_packets(reader, writer):
    print("[DEBUG CLIENT] Sætter TUN interface op lokalt...")
    TUNSETIFF = 0x400454ca
    IFF_TUN = 0x0001
    IFF_NO_PI = 0x1000
    REAL_INTERFACE = "eth0"
    REAL_GATEWAY = "192.168.1.1"

    tun = os.open("/dev/net/tun", os.O_RDWR)
    ifr = struct.pack("16sH", b"tun0", IFF_TUN | IFF_NO_PI)
    fcntl.ioctl(tun, TUNSETIFF, ifr)

    print("[DEBUG CLIENT] Konfigurerer IP og routing på client...")
    subprocess.run(["ip", "addr", "add", "10.0.0.2/24", "dev", "tun0"], check=True)
    subprocess.run(["ip", "link", "set", "tun0", "up"], check=True)
    time.sleep(1) 

    # BRUG FORSKELLIGE LINJER AN PÅ OM DET ER GLOBAL ELLER LOKAL:
    subprocess.run(["ip", "route", "replace", HOST, "dev", REAL_INTERFACE], check=True) # Lokal
#   subprocess.run(["ip", "route", "replace", HOST, "via", REAL_GATEWAY, "dev", REAL_INTERFACE], check=True) # Global
    subprocess.run(["sudo", "sysctl", "-w", "net.ipv6.conf.all.disable_ipv6=1"], check=True)

    subprocess.run(["ip", "route", "replace", "0.0.0.0/1", "dev", "tun0"], check=True)
    subprocess.run(["ip", "route", "replace", "128.0.0.0/1", "dev", "tun0"], check=True)
    print("[DEBUG CLIENT] Routing sat op. Al trafik bør nu pege på tun0.")

    loop = asyncio.get_running_loop()

    async def read_tun():
        print("[DEBUG CLIENT] 'read_tun' loop startet. Lytter efter udgående trafik på TUN...")
        while True:
            try:
                packet = await loop.run_in_executor(None, os.read, tun, 2048)
                wrapped = wrap_packet(packet)
                writer.write(wrapped)
                await writer.drain()
            except Exception as e:
                break
    
    async def write_tun():
        while True:
            try:
                packet = await unwrap_packet(reader)
                if not packet:
                    break
                await loop.run_in_executor(None, os.write, tun, packet)
                try: 
                    ip = IP(packet[:20]) 
                    print(f"[DEBUG CLIENT] (Scapy) Pakke-info: {ip.src} -> {ip.dst}")
                except: 
                    pass
            except Exception as e:
                break

    try:
        await asyncio.gather(read_tun(), write_tun())
    except asyncio.CancelledError:
        print("[DEBUG CLIENT] Tunneling blev annulleret.")

async def unwrap_packet(reader):
    raw_len = await reader.readexactly(4)
    size = struct.unpack("!I", raw_len)[0]

    packet = await reader.readexactly(size)
    return packet

async def main():
    print("[DEBUG CLIENT] Starter main...")
    reader, writer = await asyncio.open_connection(HOST, PORT)
    await handle_connection(reader, writer)

if __name__ == "__main__":
    asyncio.run(main())