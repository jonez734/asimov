# asimov/net/ping.py
# Ping/Pong utilities for connection testing

import socket
import time
from typing import Optional

from .packet import (
    encode_packet,
    decode_packet,
    PACKET_TYPE_PING,
    PACKET_TYPE_PONG,
    PONG,
)


def respond_to_ping(sock: socket.socket, addr: tuple):
    """Send a PONG response to a PING sender."""
    pong_data = encode_packet(PACKET_TYPE_PONG)
    sock.sendto(pong_data, addr)


def send_ping_and_wait_for_pong(sock: socket.socket, timeout: float = 1.0) -> bool:
    """
    Send a PING and wait for PONG response.
    Returns True if PONG received, False on timeout.
    """
    ping_data = encode_packet(PACKET_TYPE_PING)
    sock.sendto(ping_data, sock.getsockname())

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            sock.settimeout(deadline - time.time())
            data, addr = sock.recvfrom(4096)
            if data:
                result = decode_packet(data)
                if result.get("packet_type") == PONG:
                    return True
        except socket.timeout:
            break
    return False


def wait_for_pong(sock: socket.socket, timeout: float = 1.0) -> Optional[dict]:
    """Wait for a PONG response with timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            sock.settimeout(deadline - time.time())
            data, addr = sock.recvfrom(4096)
            if data:
                result = decode_packet(data)
                return result
        except socket.timeout:
            break
    return None
