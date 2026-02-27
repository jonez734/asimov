# asimov/net/tcp.py
# TCP sender/receiver classes

import socket
from typing import Optional

from .packet import Packet


class TCPSender:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None

    def connect(self):
        if self.sock is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))

    def send(self, packet: Packet):
        if self.sock is None:
            raise RuntimeError("TCPSender.send(): not connected")
        self.sock.sendall(packet.encode())

    def recv(self) -> Optional[Packet]:
        if self.sock is None:
            raise RuntimeError("TCPSender.recv(): not connected")
        return Packet.recv(self.sock)

    def close(self):
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.sock.close()
            self.sock = None


class TCPReceiver:
    def __init__(self, sock: socket.socket):
        self.sock = sock

    def recv(self) -> Optional[Packet]:
        return Packet.recv(self.sock)
