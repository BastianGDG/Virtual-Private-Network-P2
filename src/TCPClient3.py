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
HOST = "10.133.16.218"
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
    TUNSETIFF = 0x400454ca
    IFF_TUN = 0x0001
    IFF_NO_PI = 0x1000
   
    tun = os.open("/dev/net/tun", os.O_RDWR)
    
    ifr = struct.pack("16sH", b"tun0", IFF_TUN | IFF_NO_PI)
    fcntl.ioctl(tun, TUNSETIFF, ifr)

    subprocess.run(["sudo","ip","addr","add","10.0.0.2/24","dev","tun0"])
    subprocess.run(["sudo","ip","link","set","tun0","up"])
    subprocess.run(["sudo","ip","route","add","10.0.0.2/24","dev","tun0"])

    print("TUN interface oprettet: tun0") 
    
    loop = asyncio.get_running_loop()

    async def Readtun():
        while True:
            packet = await loop.run_in_executor(None, os.read, tun, 2048)
            #print("Fik packet:", packet[:20])
            writer.write(packet)
            await writer.drain()
    
    async def writetun():
        while True:
                data = await reader.read(2048)
                try:
                    ip = IP(data[:20])
                    ip.show()
                except:
                    pass
                if not data:
                    break
                await loop.run_in_executor(None, os.write, tun, data)
    try:
        await asyncio.gather(Readtun(), writetun())
    except asyncio.CancelledError:
        pass

async def main():
    reader, writer = await asyncio.open_connection(HOST, PORT)
    await handle_connection(reader, writer)


if __name__ == "__main__":
    asyncio.run(main())
