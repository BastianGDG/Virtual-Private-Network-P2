import struct


def main():
    version = 1
    packet_type = 3
    packet_id = 1024
    message = "Hemmelig besked".encode('utf-8') 

    header = struct.pack('!BBI', version, packet_type, packet_id)

    full_packet = header + message

    print(f"Rå bytes der sendes: {full_packet}")

    return full_packet
