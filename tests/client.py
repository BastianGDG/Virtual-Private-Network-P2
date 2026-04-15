import socket
import struct
import random

version = 1
packet_type = 3 
packet_id = 1024
message = "Hemmelig besked".encode('utf-8') 

header = struct.pack('!BBI', version, packet_type, packet_id)

full_packet = header + message

print(f"Rå bytes der sendes: {full_packet}")

HOST = "127.0.0.1"  
PORT = 65432  

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    s.sendall(full_packet)
    prime = s.recv(1024)
    A = s.recv(1024)
    p = s.recv(1024)
    data = s.recv(1024)
    prime = prime.decode()
    prime = int(prime,2)

    A = A.decode()
    A = int(A,2)

    p = p.decode()
    p = int(p,2)

    b = random.randrange(1,100)
    B = prime**b % p

    key = A**b % p

    B = bin(B)
    B = B.encode()

    s.sendall(B)



print(key)

print(f"Received {data!r}") 


    