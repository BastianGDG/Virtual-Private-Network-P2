import os
import subprocess
import asyncio
from scapy.all import IP
from ..config import load_client_config
from ..crypto import encrypt, hash
from ..setup import create_tun_interface, configure_client_routing
from ..comms import client_handshake, unwrap_packet, wrap_packet

HOST, PORT, MODE, PASSWORD = load_client_config()

print(f"Client configuration: HOST={HOST}, PORT={PORT}, MODE={MODE}, PASSWORD={'*' * len(PASSWORD)}")

async def handle_connection(reader, writer):
    print(f"Connected to server at: {HOST}:{PORT}")

    global PASSWORD
    PASSWORD = str(PASSWORD) + "\n"

    writer.write(PASSWORD.encode("utf-8"))
    await writer.drain()

    try:
        K = await client_handshake(reader,writer)
        K = hash(K)

        Virtual_IP = await reader.readline()
        Virtual_IP = Virtual_IP[:-1]
        
        while True:
                await send_packets(reader, writer,K,Virtual_IP)
    except ConnectionResetError:
        print(f"Connection lost (ConnectionResetError)")
    except Exception as e:
         print(f"Unexpected error: {e}")
    finally:
        print("Closing connection...")
        writer.close()
        await writer.wait_closed()

'''
async def pingTest(reader, writer):
    start = time.perf_counter()
    writer.write("Ping!".encode("utf-8"))
    await writer.drain()

    pong = await reader.read(1024)
    pong = pong.decode("utf-8")

    if pong:
        end = time.perf_counter()
        ping = int((end - start) * 1000)
        print(f"[DEBUG CLIENT] Modtog: {pong}. Din ping er {ping} ms")
    else:
        print("[DEBUG CLIENT FEJL] Kunne ikke modtage pong!")
'''

async def send_packets(reader, writer,K,VIRTUAL_IP):
    print("Setting up TUN interface locally...")
    tun = create_tun_interface()

    print("Configuring IP and routing on client...")
    configure_client_routing(VIRTUAL_IP, HOST, MODE)

    loop = asyncio.get_running_loop()

    async def read_tun():
        print("Reading from TUN interface...")

        # Client needs to send an initalizing unencrypted packet to server, to tell that client is ready
        init_packet = await wrap_packet(await loop.run_in_executor(None, os.read, tun, 2048))
        writer.write(init_packet)
        await writer.drain()

        while True:
            try:
                packet = await loop.run_in_executor(None, os.read, tun, 2048)
                wrapped = encrypt(packet,K)
                wrapped = await wrap_packet(wrapped)
                writer.write(wrapped)
            except Exception as e:
                print(f"Error: {e}")
                break
    
    async def write_tun():
        while True:
            try:
                packet = await unwrap_packet(reader,K)
                if not packet:
                    break
                await loop.run_in_executor(None, os.write, tun, packet)
               # try: 
                     # ip = IP(packet[:20]) 
                    # print(f"Packet-info: {ip.src} -> {ip.dst}")
               # except: 
                   # pass
            except Exception as e:
                print(f"Error: {e}")
                break

    try:
        await asyncio.gather(read_tun(), write_tun())
    except asyncio.CancelledError:
        print("Closing TUN interface...")

async def main():
    print("Starting main...")
    reader, writer = await asyncio.open_connection(HOST, PORT)
    await handle_connection(reader, writer)

if __name__ == "__main__":
    asyncio.run(main())