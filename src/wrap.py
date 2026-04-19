import struct
import asyncio

def wrap_packet(packet_bytes):
    length = len(packet_bytes)
    return struct.pack("!I", length) + packet_bytes
