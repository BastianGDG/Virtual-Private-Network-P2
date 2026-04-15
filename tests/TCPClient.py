import socket
import random
import time
from P2.VPN.tests.tunnel import create_tun
import os

# Define the host IP-adress
HOST = "172.20.10.2"

# Define the host port
PORT = 6789

# Open the TCP socket
CLIENT_SOCKET = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

# Initialize the connection to the host with the given IP-adress and port number
CLIENT_SOCKET.connect((HOST,PORT))

choice = 0

def ping_test():
    # Start a timer so the RTT can be measured
    start = time.perf_counter()

    # Send a message to the host, so they know they are getting pinged
    CLIENT_SOCKET.sendall("Ping!".encode("utf-8"))

    # Recieve a pong back from the server
    pong = CLIENT_SOCKET.recv(1024).decode("utf-8")

    if pong:
        # If the pong was succesfully recieved, start the timer and calculate the RTT in ms
        end = time.perf_counter()
        ping = end - start
        ping = ping * 100
        ping = int(ping)

        print(f"Your ping is {ping} ms")
    else:
        # If the pong could not be recieved, print an error message
        print("Error, could not receive pong!")

        
def key_exchange():
    # Define a sentence so the server knows we would like to do a key exchange
    sentence = "Key request"

    # Send the request
    CLIENT_SOCKET.sendall(sentence.encode("utf-8"))

    # Recieve the prime number from the server
    p = CLIENT_SOCKET.recv(1024).decode("utf-8")
    print ("p:", p)

    # Receive the generator from the server
    g = (CLIENT_SOCKET.recv(1024).decode("utf-8"))
    print ("g:", g)

    # Convert the primenumber and generator to integers, so we may do math with them
    p = int(p)
    g = int(g)

    # Generate a random integer from 50 to 1000, this is the client secret
    b = random.randint(50,1000)

    # Calculate the public number, it is calculated by: g^b % p 
    B = pow(g, b, p)
    print("B:", str(B))

    # Send the public number
    CLIENT_SOCKET.sendall(str(B).encode("utf -8"))

    # Receive the server's public number
    A = CLIENT_SOCKET.recv(1024).decode("utf -8")
    print ("A:", A)
    A = int(A)

    # Calculate the shared secret: A^b % p
    K = pow(A, b, p)
    print("Shared Key:", str(K))

def send_packets():
    tun = create_tun
    while True:
        packet = os.read(tun, 2048)
        print("Fik packet:", packet[:20])
        CLIENT_SOCKET.sendall(packet)

def main():
    print("1: Ping test")
    print("2: Key exchange")
    print("3: Create TUN interface")
    print("4: Exit")
    choice = input("Select a choice: ")
    choice = int(choice)

    if choice == 1:
        ping_test()
        main()
    elif choice == 2:
        key_exchange()
        main()
    elif choice == 3:
        send_packets()
    else:
        print("Wrong choice")

main()
CLIENT_SOCKET.close()
