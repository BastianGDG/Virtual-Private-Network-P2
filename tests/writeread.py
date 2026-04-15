import os
import socket
import select

tun_fd = ...      # TUN FD
sock = ...        # UDP/TCP socket

while True:
    r, w, _ = select.select([tun_fd, sock], [], [])

    # Fra klient til socket til TUN
    if sock in r:
        data = sock.recv(1500)
        os.write(tun_fd, data)

    # Fra OS til TUN til socket til klient
    if tun_fd in r:
        packet = os.read(tun_fd, 1500)
        sock.send(packet)