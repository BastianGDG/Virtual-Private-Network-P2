import random
from Crypto.Util import number
import asyncio
import os
import struct
import fcntl
import select
from scapy.all import IP
import subprocess

# Define host as 0.0.0.0 so that it automatically becomes the server's current IP
HOST = "0.0.0.0"
# Define which port the VPN runs on, this needs to be above 1023 as to not disturb well known services
PORT = 6789

# Define TUN parameters
TUNSETIFF = 0x400454ca
IFF_TUN   = 0x0001
IFF_NO_PI = 0x1000

TUN = os.open("/dev/net/tun", os.O_RDWR)

ifr = struct.pack("16sH", b"tun0", IFF_TUN | IFF_NO_PI)
fcntl.ioctl(TUN, TUNSETIFF, ifr)

os.set_blocking(TUN,False)

print("TUN interface oprettet: tun0")

subprocess.run(["ip","addr","add","10.0.0.1/24","dev","tun0"])
subprocess.run(["ip","link","set","tun0","up"])
subprocess.run(["sudo","iptables", "-t", "nat", "-A","POSTROUTING","-o","eth0","-j","MASQUERADE"])
subprocess.run(["sudo","sysctl","-w","net.ipv4.ip_forward=1"])
subprocess.run(["sudo","sysctl","-w","net.ipv6.conf.all.forwarding=1"])

# Nye commands
subprocess.run(["sudo","iptables","-A","FORWARD","-i","tun0","-o","eth0","-j","ACCEPT"])
subprocess.run(["sudo","iptables","-A","FORWARD","-i","eth0","-o","tun0","-j","ACCEPT"])

# socket til TUN
async def socket_to_tun(reader):
    i = 0
    while True:
        if i <= 3:
            i += 1
            continue
        else:
            packet = await unwrap_packet(reader)

            if not packet:
                print("Client disconnected")
                break
        
            print(f"Skriver {len(packet)} bytes til TUN", flush=True)
            os.write(TUN, packet)
            print("til TUN")
            i += 1


# TUN til socket
async def tun_to_socket(writer):
    loop = asyncio.get_running_loop()

    while True:
        packet = await loop.run_in_executor(None, os.read, TUN, 2048)

        writer.write(await wrap_packet(packet))
        await writer.drain()
        print("til socket")


async def handle_client(reader, writer):
    addr = writer.get_extra_info("peername")
    print(f"Client connected: {addr}")
    try:
        await asyncio.gather(
        socket_to_tun(reader),
        tun_to_socket(writer)
        )
    except asyncio.IncompleteReadError:
        print(f"Client disconnected: {addr}")
    except Exception as e:
        print(f"Fejl i handle_client: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

async def key_exchange(reader, writer, addr):
    print(f"Starting key exchange with {addr}...")
    
    # Get q as a 1024 bit prime number
    q = number.getPrime(1024)
    print("q:", q)

    # Generate p with q, this is a safe prime
    p = 2 * q + 1
    print("p:", p)

    # Generate the generator, it cant give 1 when taken to the power of 2 and mod p
    # or when taken to the power of q and mod p, as this is a bad generator
    # it will keep generating new generators until the requirements are met
    g = random.randrange(2, p-1)
    while g**2 % p == 1 and g**q % p == 1:
        g = random.randrange(2, p-1)
    print("g:", g)

    # Send p and g
    writer.write(str(p).encode("utf-8"))
    await writer.drain()
    writer.write(str(g).encode("utf-8"))
    await writer.drain()

    # Generate our secret and public parts
    a = random.randint(1, 100)
    A = g**a % p
    print("A:", A)

    # Wait for the client to send their public part (B)
    B_bytes = await reader.read(1024)
    if not B_bytes: # If nothing, client has dropped
        return 
        
    B = B_bytes.decode("utf-8")
    print("B:", B)

    # Send our public part (A)
    writer.write(str(A).encode("utf-8"))
    await writer.drain()

    # Calculate shared secret
    K = int(B)**a % p
    print(f"Shared secret key K for {addr}:", K)

async def unwrap_packet(reader):
    try:
        raw_len = await reader.readexactly(4)
        size = struct.unpack("!I", raw_len)[0]
        print (f"size is {size}")
        packet = await reader.readexactly(size)
        return packet
    except:
        return None

async def wrap_packet(packet_bytes):
    length = len(packet_bytes)
    return struct.pack("!I", length) + packet_bytes

async def main():
    # Start the async server
    server = await asyncio.start_server(handle_client, HOST, PORT)
    
    # Get the server IP
    addr = server.sockets[0].getsockname()
    print(f"Async Server is ready and listening on {addr}...")

    # Keep the server running forever
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    # This is the only place we call asyncio.run()
    asyncio.run(main())