import os
import fcntl
import struct
import subprocess
import time

# Constants for TUN/TAP
TUNSETIFF = 0x400454ca
IFF_TUN   = 0x0001
IFF_NO_PI = 0x1000

def create_tun_interface(name=b"tun0"):
    """Creates and returns a file descriptor for a TUN interface."""
    tun = os.open("/dev/net/tun", os.O_RDWR)
    ifr = struct.pack("16sH", name, IFF_TUN | IFF_NO_PI)
    fcntl.ioctl(tun, TUNSETIFF, ifr)
    return tun

def configure_client_routing(virtual_ip, host_ip, mode):
    """Configures the local routing table for the client."""
    # Get current gateway and interface
    cmd = ["ip", "route", "show", "default"]
    result = subprocess.check_output(cmd).decode('utf-8')
    real_gateway = result.split()[2]
    real_interface = result.split()[4]

    # Bring interface up
    subprocess.run(["ip", "addr", "add", virtual_ip, "dev", "tun0"], check=True)
    subprocess.run(["ip", "link", "set", "tun0", "up"], check=True)
    # time.sleep(1) 

    # Route VPN server traffic through the real physical gateway so we don't loop
    if mode == "local":
        subprocess.run(["ip", "route", "replace", host_ip, "dev", real_interface], check=True)
    elif mode == "global":   
        subprocess.run(["ip", "route", "replace", host_ip, "via", real_gateway, "dev", real_interface], check=True)

    # Disable IPv6 and route all traffic through TUN
    subprocess.run(["sudo", "sysctl", "-w", "net.ipv6.conf.all.disable_ipv6=1"], check=True)
    subprocess.run(["ip", "route", "replace", "0.0.0.0/1", "dev", "tun0"], check=True)
    subprocess.run(["ip", "route", "replace", "128.0.0.0/1", "dev", "tun0"], check=True)

def configure_server_routing(real_interface):
    """Configures iptables and IP forwarding for the server."""
    subprocess.run(["ip", "addr", "add", "10.0.0.254/24", "dev", "tun0"])
    subprocess.run(["ip", "link", "set", "tun0", "up"])
    
    # Enable NAT and Forwarding
    subprocess.run(["sudo", "iptables", "-t", "nat", "-A", "POSTROUTING", "-o", real_interface, "-j", "MASQUERADE"])
    subprocess.run(["sudo", "sysctl", "-w", "net.ipv4.ip_forward=1"])
    subprocess.run(["sudo", "iptables", "-A", "FORWARD", "-i", "tun0", "-o", real_interface, "-j", "ACCEPT"])
    subprocess.run(["sudo", "iptables", "-A", "FORWARD", "-i", real_interface, "-o", real_interface, "-j", "ACCEPT"])