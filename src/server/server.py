import asyncio
import os
import struct
import socket
from ..crypto import encrypt, hash
from ..config import load_server_config
from .peer import create_peer, flush_table, lookup
from ..setup import create_tun_interface, configure_server_routing
from ..comms import server_handshake, wrap_packet, unwrap_packet

# Server configuration
HOST = "0.0.0.0"
PORT = 6789

# Load server password from input or config file
PASSWORD = load_server_config()

# If password was inputted, hash it, otherwise PASSWORD will be None and the server will not require authentication
if PASSWORD:
    PASSWORD = hash(PASSWORD)

# Global variable to keep track of connected clients, this is used to give unique IDs to clients as they connect
CLIENT_COUNT = 0

CLIENTS = {}

# Set up TUN interface and network configuration
print("[DEBUG SERVER] Setting up TUN interface...")
TUN = create_tun_interface()

print("[DEBUG SERVER] TUN interface created: tun0")

# Configure IP and routing on server
configure_server_routing()
print("[DEBUG SERVER] Network configuration and iptables rules applied.")

# Flush peer table on server start, to make sure no old peers are present
flush_table()

async def socket_to_tun(reader,K):
    while True:
        try:
            packet = await unwrap_packet(reader,K)
            if not packet:
                break
            os.write(TUN, packet)
        except asyncio.IncompleteReadError as e:
            print(f"Error: {e}")
            break
        except Exception as e:
            print(f"Error: {e}")
            break

async def tun_to_socket(writer,K):
    loop = asyncio.get_running_loop()
    while True:
        try:
            packet = await loop.run_in_executor(None, os.read, TUN, 2048)
            dest_ip_bytes = packet[16:20]
            dest = socket.inet_ntoa(dest_ip_bytes)

            ID = dest.split(".")
            ID = ID[-1]
            
            peer = lookup(ID)

            if peer:
                Ip = getattr(peer,"IP")
                writer = CLIENTS.get(Ip)

                K = getattr(peer,"key")
                K = bytes.fromhex(K)

                wrapped = encrypt(packet,K)
                wrapped = await wrap_packet(wrapped)
                writer.write(wrapped)
            else:
                pass
        except Exception as e:
            pass

async def handle_client(reader, writer):
    addr = writer.get_extra_info("peername")
    print(f"\n[DEBUG SERVER] New client connected: {addr}")
    
    input_password = await reader.readline()
    input_password = input_password.decode("utf-8", errors="ignore")
    input_password = input_password.removesuffix("\n")
    input_password = hash(input_password)

    try:
        if input_password == PASSWORD:
            K = await server_handshake(reader, writer, addr)
            K = hash(K)

            K = K.hex()

            global CLIENT_COUNT
            CLIENT_COUNT += 1

            ip = addr[0]

            CLIENTS[ip] = writer

            peer = create_peer(str(CLIENT_COUNT), addr[0], K)
            K = bytes.fromhex(K)

            Virtual_IP = getattr(peer,"Virtual_IP")
            Virtual_IP = Virtual_IP + "\n"
            writer.write(Virtual_IP.encode("utf-8"))
            await writer.drain()

            while True:
                data = await reader.read(2048)
                if not data:
                    print("[DEBUG SERVER] handle_client: received empty data, closing connection.")
                    break
                    
                elif len(data) > 4:
                    length = struct.unpack("!I", data[:4])[0]

                    first_packet = data[4:4+length]
                    os.write(TUN, first_packet)

                    await asyncio.gather(
                        socket_to_tun(reader,K),
                        tun_to_socket(writer,K)
                    )
                    print("[DEBUG SERVER] handle_client: TUN Loop ended, closing connection.")
                    break 
                else:
                    print(f"[DEBUG SERVER] handle_client: received very short/unknown data: {data}")
                
    except Exception as e:
        print(f"[DEBUG SERVER FAILED] in handle_client: {e}")
    finally:
        print(f"[DEBUG SERVER] Closing connection to {addr}")
        writer.close()
        await writer.wait_closed()

async def main():
    server = await asyncio.start_server(handle_client, HOST, PORT)
    addr = server.sockets[0].getsockname()
    print(f"[DEBUG SERVER] Async Server is ready and listening on {addr}...")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())