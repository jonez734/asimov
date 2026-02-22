# demo_net_tcp_pingpong.py

import argparse
import threading
import socket
import struct
import time

from asimov import io
from asimov.net import Packet, TCPSender, TCPReceiver, retry_until_connected


PACKET_TYPE_PING = 1
PACKET_TYPE_PONG = 2


def handle_ping(packet: Packet, sender: TCPSender):
    """Reply to a PING with a PONG, preserving timestamp."""
    pong_payload = struct.pack("!d", packet.timestamp)
    pong = Packet(PACKET_TYPE_PONG, pong_payload)
    sender.send(pong)
    io.echo("[Server] PING -> PONG")


def handle_pong(packet: Packet):
    """Handle a received PONG packet."""
    (orig_ts,) = struct.unpack("!d", packet.payload)
    rtt = time.time() - orig_ts
    io.echo(f"[Client] RTT: {rtt*1000:.1f}ms")


def server_thread(host: str, port: int):
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind((host, port))
    server_sock.listen(1)
    io.echo(f"[Server] Listening on {host}:{port}")

    conn, addr = server_sock.accept()
    io.echo(f"[Server] Connection from {addr}")

    receiver = TCPReceiver(conn)
    sender = TCPSender(host, port)
    sender.sock = conn

    while True:
        pkt = receiver.recv()
        if pkt is None:
            io.echo("[Server] Client disconnected")
            break
        if pkt.ptype == PACKET_TYPE_PING:
            handle_ping(pkt, sender)


def client_thread(host: str, port: int, interval: float):
    sock = retry_until_connected(host, port, retries=10, delay=0.5)
    client = TCPSender(host, port)
    client.sock = sock
    receiver = TCPReceiver(sock)

    while True:
        ping_pkt = Packet(PACKET_TYPE_PING)
        client.send(ping_pkt)
        io.echo("[Client] Sent PING")

        pkt = receiver.recv()
        if pkt is None:
            io.echo("[Client] Server disconnected")
            break
        if pkt.ptype == PACKET_TYPE_PONG:
            handle_pong(pkt)

        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TCP PING/PONG Demo")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Server host")
    parser.add_argument("--port", type=int, default=9999, help="Server port")
    parser.add_argument("--interval", type=float, default=2.0, help="PING interval (seconds)")
    args = parser.parse_args()

    io.echo(f"TCP PING/PONG Demo - {args.host}:{args.port}")

    t = threading.Thread(target=server_thread, args=(args.host, args.port), daemon=True)
    t.start()

    client_thread(args.host, args.port, args.interval)
