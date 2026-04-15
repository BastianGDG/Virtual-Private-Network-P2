import random
from Crypto.Util import number
import asyncio
import os
import struct
import fcntl
import subprocess

# Define host as 0.0.0.0
HOST = "0.0.0.0"
PORT = 6789

# Define TUN parameters
TUNSETIFF = 0x400454ca
IFF_TUN   = 0x0001
IFF_NO_PI = 0x1000

# Initialize TUN Interface
TUN = os.open("/dev/net/tun", os.O_RDWR)
ifr = struct.pack("16sH", b"tun0", IFF_TUN | IFF_NO_PI)
fcntl.ioctl(TUN, TUNSETIFF, ifr)

print("TUN interface oprettet: tun0")

# Network Setup
subprocess.run(["ip","addr","add","10.0.0.1/24","dev","tun0"])
subprocess.run(["ip","link","set","tun0","up"])
subprocess.run(["sudo", "ip", "route", "add", HOST, "via", "10.133.16.26"])
subprocess.run(["sudo","iptables", "-t", "nat", "-A","POSTROUTING","-o","eth0","-j","MASQUERADE"])
subprocess.run(["sudo","sysctl","-w","net.ipv4.ip_forward=1"])
subprocess.run(["sudo","sysctl","-w","net.ipv6.conf.all.forwarding=1"])

class VPNProtocol(asyncio.DatagramProtocol):
    # Handles UDP traffic: Socket -> TUN
    def __init__(self):
        self.transport = None
        self.client_addr = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        # Update the client address dynamically whenever a packet arrives
        self.client_addr = addr
        # Write the incoming UDP packet directly to the TUN interface
        os.write(TUN, data)
        # print(f"UDP -> TUN from {addr}")

    def error_received(self, exc):
        print(f"UDP Error: {exc}")

async def tun_to_socket(protocol):
    """Handles TUN traffic: TUN -> Socket"""
    loop = asyncio.get_running_loop()
    while True:
        # Read a packet from the virtual interface
        packet = await loop.run_in_executor(None, os.read, TUN, 2048)
        
        # If we have a known client address, send the packet back via UDP
        if protocol.transport and protocol.client_addr:
            protocol.transport.sendto(packet, protocol.client_addr)
            # print("TUN -> UDP")

async def main():
    loop = asyncio.get_running_loop()

    # Create the UDP endpoint instead of a TCP server
    # This returns a (transport, protocol) tuple
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: VPNProtocol(),
        local_addr=(HOST, PORT)
    )
    
    print(f"UDP VPN Server is ready and listening on {HOST}:{PORT}...")

    # Start the reverse direction (TUN to Socket) as a background task
    try:
        await tun_to_socket(protocol)
    except Exception as e:
        print(f"Server Error: {e}")
    finally:
        transport.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped by user.")