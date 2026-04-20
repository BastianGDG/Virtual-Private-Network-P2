import random
from Crypto.Util import number
import asyncio
import os
import struct
import fcntl
import select
from scapy.all import IP
import subprocess
from wrap import wrap_packet

HOST = "0.0.0.0"
PORT = 6789

TUNSETIFF = 0x400454ca
IFF_TUN   = 0x0001
IFF_NO_PI = 0x1000

print("[DEBUG SERVER] Sætter TUN interface op...")
TUN = os.open("/dev/net/tun", os.O_RDWR)

ifr = struct.pack("16sH", b"tun0", IFF_TUN | IFF_NO_PI)
fcntl.ioctl(TUN, TUNSETIFF, ifr)

print("[DEBUG SERVER] TUN interface oprettet: tun0")

subprocess.run(["ip","addr","add","10.0.0.1/24","dev","tun0"])
subprocess.run(["ip","link","set","tun0","up"])
subprocess.run(["sudo","iptables", "-t", "nat", "-A","POSTROUTING","-o","eth0","-j","MASQUERADE"])
subprocess.run(["sudo","sysctl","-w","net.ipv4.ip_forward=1"])
subprocess.run(["sudo","sysctl","-w","net.ipv6.conf.all.forwarding=1"])
subprocess.run(["sudo","iptables","-A","FORWARD","-i","tun0","-o","eth0","-j","ACCEPT"])
subprocess.run(["sudo","iptables","-A","FORWARD","-i","eth0","-o","tun0","-j","ACCEPT"])
print("[DEBUG SERVER] Netværkskonfiguration og iptables regler anvendt.")

async def socket_to_tun(reader):
    while True:
        try:
            packet = await unwrap_packet(reader)
            if not packet:
                break
            os.write(TUN, packet)
        except asyncio.IncompleteReadError as e:
            break
        except Exception as e:
            break

async def tun_to_socket(writer):
    loop = asyncio.get_running_loop()
    while True:
        try:
            packet = await loop.run_in_executor(None, os.read, TUN, 2048)
            wrapped = wrap_packet(packet)
            writer.write(wrapped)
            await writer.drain()
        except Exception as e:
            break

async def handle_client(reader, writer):
    addr = writer.get_extra_info("peername")
    print(f"\n[DEBUG SERVER] Ny client forbundet: {addr}")

    try:
        while True:
            data = await reader.read(1024)
            if not data:
                print("[DEBUG SERVER] handle_client: Modtog 0 bytes, client har lukket forbindelsen.")
                break
                
            msg = data.decode("utf-8", errors="ignore")
            
            if "Ping!" in msg:
                print(f"[DEBUG SERVER] Ping modtaget fra {addr}")
                writer.write("Pong!".encode("utf-8"))
                await writer.drain()
            
            elif "Key request" in msg:
                print(f"[DEBUG SERVER] Key request modtaget fra {addr}")
                await key_exchange(reader, writer, addr)
                
            elif len(data) > 4:
                length = struct.unpack("!I", data[:4])[0]

                first_packet = data[4:4+length]
                os.write(TUN, first_packet)
                await asyncio.gather(
                    socket_to_tun(reader),
                    tun_to_socket(writer)
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
    q = number.getPrime(1024)
    p = 2 * q + 1
    g = random.randrange(2, p-1)
    while g**2 % p == 1 and g**q % p == 1:
        g = random.randrange(2, p-1)

    print(f"p: {p}")
    print(f"q: {q}")

    writer.write(str(p).encode("utf-8"))
    await writer.drain()
    writer.write(str(g).encode("utf-8"))
    await writer.drain()

    a = random.randint(1, 100)
    A = g**a % p

    print(f"A: {A}")

    B_bytes = await reader.read(1024)
    if not B_bytes:
        return 
        
    B = B_bytes.decode("utf-8")
    writer.write(str(A).encode("utf-8"))
    await writer.drain()

    print(f"B: {B}")

    K = int(B)**a % p
    print(f"Shared secret key K for {addr}: {K}")

async def unwrap_packet(reader):
    raw_len = await reader.readexactly(4)
    size = struct.unpack("!I", raw_len)[0]

    packet = await reader.readexactly(size)
    return packet

async def main():
    server = await asyncio.start_server(handle_client, HOST, PORT)
    addr = server.sockets[0].getsockname()
    print(f"[DEBUG SERVER] Async Server is ready and listening on {addr}...")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())