import socket
import random
import time
import os
import fcntl
import struct
import subprocess
import asyncio
from scapy.all import IP

#Indstast Host server IP herunder
HOST = "10.133.16.147"
PORT = 6789
choice = 0

async def handle_connection(reader, writer):
    print(f"Connected to server")

    try:
        while True:
            print("1: Ping test")
            print("2: Key exchange")
            print("3: Create TUN interface")
            print("4: Exit")
            choice = await asyncio.to_thread(input, "Select a choice: ")
            choice = int(choice)
    
            if choice == 1:
                await pingTest(reader, writer)
            elif choice == 2:
                await keyExchange(reader, writer)
            elif choice == 3:
                await send_packets(reader, writer)
            else:
                print("Wrong choice")
      
    except ConnectionResetError:
        print(f"Connection lost")
    finally:
        writer.close()
        await writer.wait_closed()

async def pingTest(reader, writer):
    start = time.perf_counter()
    writer.write("Ping!".encode("utf-8"))
    await writer.drain()


    pong = reader.read(1024).decode("utf-8")

    if pong:
        end = time.perf_counter()
        ping = end - start
        ping = ping * 100
        ping = int(ping)

        print(f"Your ping is {ping} ms")
    else:
        print("Error, could not receive pong!")

        
async def keyExchange(reader, writer):
    sentence = "Key request"
    writer.write(sentence.encode("utf -8"))
    await writer.drain()
    p = await reader.read(1024).decode("utf -8")
    print ("p:", p)
    g = await reader.read(1024).decode("utf -8")
    print ("g:", g)

    p = int(p)
    g = int(g)
    b = random.randint(1,100)
    B = pow(g, b, p)
    print("B:", str(B))
    writer.write(str(B).encode("utf -8"))
    await writer.drain()
    A = (await reader.read(1024)).decode("utf -8")
    print ("A:", A)
    A = int(A)

    K = pow(A, b, p)
    print("Shared Key:", str(K))

async def send_packets(reader, writer):
    # 1. SIGNAL THE SERVER: Switch to tunnel mode
    writer.write("Start Tunnel".encode("utf-8"))
    await writer.drain()

    # 2. Setup TUN Interface
    tun = os.open("/dev/net/tun", os.O_RDWR)
    ifr = struct.pack("16sH", b"tun0", 0x0001 | 0x1000) # IFF_TUN | IFF_NO_PI
    fcntl.ioctl(tun, 0x400454ca, ifr)
    os.set_blocking(tun, False) # Non-blocking

    # 3. Routing (Be careful with 0.0.0.0/1 if on a remote server!)
    subprocess.run(["ip", "addr", "add", "10.0.0.2/24", "dev", "tun0"], check=True)
    subprocess.run(["ip", "link", "set", "tun0", "up"], check=True)
    
    # Use specific route for the VPN HOST to prevent a loop
    subprocess.run(["ip", "route", "add", HOST, "via", "10.133.16.26"], check=True)
    
    # Redirect traffic into the tunnel
    subprocess.run(["ip", "route", "add", "0.0.0.0/1", "dev", "tun0"], check=True)
    subprocess.run(["ip", "route", "add", "128.0.0.0/1", "dev", "tun0"], check=True)

    loop = asyncio.get_running_loop()
    queue = asyncio.Queue()

    # TUN -> Socket loop
    def read_callback():
        try:
            packet = os.read(tun, 2048)
            queue.put_nowait(packet)
        except: pass

    loop.add_reader(tun, read_callback)

    async def write_to_socket():
        while True:
            packet = await queue.get()
            writer.write(wrap_packet(packet))
            await writer.drain()

    # Socket -> TUN loop
    async def read_from_socket():
        while True:
            packet = await unwrap_packet(reader)
            if not packet: break
            os.write(tun, packet)

    try:
        await asyncio.gather(write_to_socket(), read_from_socket())
    finally:
        loop.remove_reader(tun)
        os.close(tun)

async def unwrap_packet(reader):
    raw_len = await reader.readexactly(4)
    size = struct.unpack("!I", raw_len)[0]

    packet = await reader.readexactly(size)
    return packet

def wrap_packet(packet_bytes):
    length = len(packet_bytes)
    return struct.pack("!I", length) + packet_bytes

async def main():
    reader, writer = await asyncio.open_connection(HOST, PORT)
    await handle_connection(reader, writer)


if __name__ == "__main__":
    asyncio.run(main())