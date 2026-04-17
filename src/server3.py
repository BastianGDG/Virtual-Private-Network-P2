import asyncio
import os
import struct
import fcntl
import subprocess

# Define host as 0.0.0.0 so that it automatically becomes the server's current IP
HOST = "0.0.0.0"
# Define which port the VPN runs on
PORT = 6789

# Define TUN parameters
TUNSETIFF = 0x400454ca
IFF_TUN   = 0x0001
IFF_NO_PI = 0x1000

TUN = os.open("/dev/net/tun", os.O_RDWR)

ifr = struct.pack("16sH", b"tun0", IFF_TUN | IFF_NO_PI)
fcntl.ioctl(TUN, TUNSETIFF, ifr)

os.set_blocking(TUN, True)

print("TUN interface oprettet: tun0")

def run_cmd(cmd):
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ ERROR: Command failed: {' '.join(cmd)}")
        print(f"Details: {result.stderr.strip()}")
    else:
        print(f"✅ Success")

run_cmd(["ip", "addr", "add", "10.0.0.1/24", "dev", "tun0"])
run_cmd(["ip", "link", "set", "tun0", "up"])
run_cmd(["iptables", "-t", "nat", "-A", "POSTROUTING", "-o", "eth0", "-j", "MASQUERADE"])
run_cmd(["sysctl", "-w", "net.ipv4.ip_forward=1"])
run_cmd(["sysctl", "-w", "net.ipv6.conf.all.forwarding=1"])
run_cmd(["iptables", "-A", "FORWARD", "-i", "tun0", "-o", "eth0", "-j", "ACCEPT"])
run_cmd(["iptables", "-A", "FORWARD", "-i", "eth0", "-o", "tun0", "-j", "ACCEPT"])

async def socket_to_tun(reader):
    while True:
        packet = await unwrap_packet(reader)
        if not packet:
            break
        # print(f"Server: Skriver {len(packet)} bytes til TUN")
        os.write(TUN, packet)

async def tun_to_socket(writer):
    loop = asyncio.get_running_loop()
    while True:
        packet = await loop.run_in_executor(None, os.read, TUN, 2048)
        # print(f"Server: Læst {len(packet)} bytes fra TUN, sender til socket")
        writer.write(wrap_packet(packet))
        await writer.drain()

async def handle_client(reader, writer):
    addr = writer.get_extra_info("peername")
    print(f"Client connected: {addr}")
    try:
        await asyncio.gather(
            socket_to_tun(reader),
            tun_to_socket(writer)
        )
    except asyncio.IncompleteReadError:
        pass
    except Exception as e:
        print(f"Fejl i handle_client: {e}")
    finally:
        print(f"Client disconnected: {addr}")
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
    server = await asyncio.start_server(handle_client, HOST, PORT)
    addr = server.sockets[0].getsockname()
    print(f"VPN Server is ready and listening on {addr}...")
    
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())