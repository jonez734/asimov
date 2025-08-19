# net.py
import socket
import struct
import time
from typing import Optional, Tuple

# ------------------------
# Helpers
# ------------------------
def recv_all(sock: socket.socket, length: int) -> Optional[bytes]:
    """Receive exactly `length` bytes from a TCP socket, or None if closed."""
    data = bytearray()
    while len(data) < length:
        try:
            chunk = sock.recv(length - len(data))
        except socket.error as e:
            print(f"recv_all(): socket error: {e}")
            return None
        if not chunk:
            return None
        data.extend(chunk)
    return bytes(data)


def recv_udp(sock: socket.socket, bufsize: int = 4096) -> Tuple[Optional[bytes], Optional[Tuple[str,int]]]:
    """Receive a single datagram from a UDP socket."""
    try:
        data, addr = sock.recvfrom(bufsize)
        return data, addr
    except socket.error as e:
        print(f"recv_udp(): socket error: {e}")
        return None, None


def send_with_length(conn: socket.socket, payload: bytes):
    """
    Send a length-prefixed payload (4-byte big-endian length + data).
    This allows TCP packets larger than typical buffer sizes to be sent
    while keeping the connection open for multiple messages.
    """
    length_prefix = struct.pack("!I", len(payload))
    conn.sendall(length_prefix + payload)


def recv_with_length(conn: socket.socket) -> bytes:
    """
    Receive a length-prefixed payload.
    First reads 4 bytes for the length, then reads exactly that many bytes.
    """
    def recv_exactly(n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = conn.recv(n - len(buf))
            if not chunk:
                raise EOFError("Connection closed before full payload received")
            buf += chunk
        return buf

    length_bytes = recv_exactly(4)
    (length,) = struct.unpack("!I", length_bytes)
    return recv_exactly(length)

def retry_until_connected(host: str, port: int, retries: int = 5, delay: float = 0.2) -> socket.socket:
    """
    Attempt to connect to a TCP host:port, retrying `retries` times with `delay` seconds between attempts.
    Returns a connected socket, or raises the last exception if all retries fail.
    """
    last_exc: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            return sock
        except Exception as e:
            last_exc = e
            print(f"[tcp_connect_retry] Attempt {attempt} failed, retrying in {delay}s...")
            time.sleep(delay)
    raise last_exc

# ------------------------
# Packet class
# ------------------------
class Packet:
    """
    Packet with type, payload, timestamp.
    Serialized as: [type (I)][timestamp (d)][payload length (I)][payload]
    """
    def __init__(self, ptype: int, payload: bytes = b"", timestamp: float = None):
        self.ptype = ptype
        self.payload = payload
        self.timestamp = timestamp if timestamp is not None else time.time()

    def encode(self) -> bytes:
        payload_len = len(self.payload)
        header = struct.pack("!IdI", self.ptype, self.timestamp, payload_len)
        return header + self.payload

    @staticmethod
    def decode(data: bytes) -> "Packet":
        if len(data) < 16:
            raise ValueError("Packet data too short")
        ptype, timestamp, payload_len = struct.unpack("!IdI", data[:16])
        payload = data[16:16+payload_len]
        return Packet(ptype, payload, timestamp)

    @staticmethod
    def recv(sock: socket.socket) -> Optional["Packet"]:
        header = recv_all(sock, 16)
        if header is None:
            return None
        ptype, timestamp, payload_len = struct.unpack("!IdI", header)
        payload = recv_all(sock, payload_len)
        if payload is None:
            return None
        return Packet(ptype, payload, timestamp)

# ------------------------
# TCP classes
# ------------------------
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

# ------------------------
# UDP classes
# ------------------------
class UDPSender:
    def __init__(self, host: str, port: int):
        self.addr = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, packet: Packet):
        self.sock.sendto(packet.encode(), self.addr)

    def close(self):
        self.sock.close()

class UDPReceiver:
    def __init__(self, host: str, port: int, bufsize: int = 4096):
        self.addr = (host, port)
        self.bufsize = bufsize
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(self.addr)

    def recv(self) -> Optional[Packet]:
        data, addr = recv_udp(self.sock, self.bufsize)
        if data is None:
            return None
        return Packet.decode(data)

    def close(self):
        self.sock.close()
