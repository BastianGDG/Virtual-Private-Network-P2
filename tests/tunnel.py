import os
import fcntl
import struct


def create_tun():
    TUNSETIFF = 0x400454ca
    IFF_TUN   = 0x0001
    IFF_NO_PI = 0x1000

    tun = os.open("/dev/net/tun", os.O_RDWR)

    ifr = struct.pack("16sH", b"tun0", IFF_TUN | IFF_NO_PI)
    fcntl.ioctl(tun, TUNSETIFF, ifr)

    print("TUN interface oprettet: tun0")
    return tun

        
