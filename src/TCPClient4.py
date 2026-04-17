import os
import fcntl
import struct
import subprocess
import asyncio
from scapy.all import IP

# Indstast Host server IP herunder
HOST = "10.133.16.147"
PORT = 6789

def run_cmd(cmd):
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ ERROR: Command failed: {' '.join(cmd)}")
        print(f"Details: {result.stderr.strip()}")
    else:
        print(f"✅ Success")

async def handle_connection(reader, writer):
    print(f"Connected to VPN server at {HOST}:{PORT}")
    
    TUNSETIFF = 0x400454ca
    IFF_TUN = 0x0001
    IFF_NO_PI = 0x1000

    REAL_INTERFACE = "eth0"
    REAL_GATEWAY = "10.133.16.26"

    tun = os.open("/dev/net/tun", os.O_RDWR)
    ifr = struct.pack("16sH", b"tun0", IFF_TUN | IFF_NO_PI)
    fcntl.ioctl(tun, TUNSETIFF, ifr)

    run_cmd(["ip", "addr", "add", "10.0.0.2/24", "dev", "tun0"])
    run_cmd(["ip", "link", "set", "tun0", "up"])
    
    # Give the interface a moment to come up
    await asyncio.sleep(1) 

    print("Configuring routing tables...")
    run_cmd(["ip", "route", "replace", HOST, "via", REAL_GATEWAY, "dev", REAL_INTERFACE])
    run_cmd(["sysctl", "-w", "net.ipv6.conf.all.disable_ipv6=1"])
    run_cmd(["ip", "route", "replace", "0.0.0.0/1", "dev", "tun0"])
    run_cmd(["ip", "route", "replace", "128.0.0.0/1", "dev", "tun0"])

    print("Tunnel is active!")
    loop = asyncio.get_running_loop()

    async def read_tun():
        while True:
            packet = await loop.run_in_executor(None, os.read, tun, 2048)
            writer.write(wrap_packet(packet))
            await writer.drain()
            # print(f"Client: Læst {len(packet)} bytes fra TUN, sendt til socket") 
    
    async def write_tun():
        while True:
            packet = await unwrap_packet(reader)
            if not packet:
                break
            await loop.run_in_executor(None, os.write, tun, packet)
            # try: 
            #     ip = IP(packet) 
            #     print(f"Client: Modtog fra server -> {ip.src} til {ip.dst}")
            # except: 
            #     pass

    try:
        await asyncio.gather(read_tun(), write_tun())
    except asyncio.IncompleteReadError:
        print("Connection lost to server.")
    except Exception as e:
        print(f"Error in connection: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

async def unwrap_packet(reader):
    raw_len = await reader.readexactly(4)
    size = struct.unpack("!I", raw_len)[0]
    packet = await reader.readexactly(size)
    return packet

def wrap_packet(packet_bytes):
    length = len(packet_bytes)
    return struct.pack("!I", length) + packet_bytes

async def main():
    try:
        reader, writer = await asyncio.open_connection(HOST, PORT)
        await handle_connection(reader, writer)
    except ConnectionRefusedError:
        print(f"Failed to connect to {HOST}:{PORT}. Is the server running?")

if __name__ == "__main__":
    asyncio.run(main())