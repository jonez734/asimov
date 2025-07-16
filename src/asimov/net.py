# asimov/net.py
import socket
import struct
import threading
import cv2
import numpy as np

from bbsengine6 import io

# Packet types
PACKET_TYPE_PING = 1
PACKET_TYPE_PONG = 2
PACKET_TYPE_EOS = 3
PACKET_TYPE_FRAME = 4

MAX_PACKET_SIZE = 1500

PACKET_TYPE = { PACKET_TYPE_PING: "PING", PACKET_TYPE_PONG: "PONG", PACKET_TYPE_EOS: "EOS", PACKET_TYPE_FRAME: "FRAME" }

HEADER_FORMAT = "!BIHHH"  # network order: packet_type (1), frame_id (4), chunk_id (2), total_chunks (2), payload_size (2)
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

PACKET_LABEL = { PACKET_TYPE_PING: "PING", PACKET_TYPE_PONG: "PONG", PACKET_TYPE_EOS: "EOS", PACKET_TYPE_FRAME: "FRAME" }

def respond_to_ping(sender_addr):
    io.echo(f"[net] PONG: {sender_addr=}")
    responder = UDPSender(sender_addr[0], sender_addr[1])
    responder.send_pong()
    responder.close()

def encode_packet(packet_type, frame_id, chunk_id, total_chunks, payload):
    """
    Encode a packet with header and payload.
    """
    header = struct.pack(HEADER_FORMAT, packet_type, frame_id, chunk_id, total_chunks, len(payload))
    return header + payload

def decode_packet(data):
    """
    Decode a packet and return (packet_type, frame_id, chunk_id, total_chunks, payload).
    """
    header = data[:HEADER_SIZE]
    payload = data[HEADER_SIZE:]
    packet_type, frame_id, chunk_id, total_chunks, payload_size = struct.unpack(HEADER_FORMAT, header)
    return packet_type, frame_id, chunk_id, total_chunks, payload[:payload_size]

def send_ping_and_wait_for_pong(sender, timeout=1.0, retry=3, packetsize=1500):
    """
    Sends a PING using UDPSender and waits for a PONG.

    Parameters:
        sender (UDPSender): The configured UDPSender instance.
        timeout (float): Timeout in seconds to wait for each PONG attempt.
        retry (int): Number of times to retry sending a PING.
        packetsize (int): Maximum size of a UDP packet to receive.

    Returns:
        bool: True if a PONG is received within the retry limit, False otherwise.
    """

    # Save current timeout
    original_timeout = sender.sock.gettimeout()
    sender.sock.settimeout(timeout)

    try:
        for attempt in range(retry):
            print(f"asimov.net.100: attempt {attempt+1}, sending PING to {sender.addr}")
            sender.send_ping()

            try:
                data, src = sender.sock.recvfrom(packetsize)
                print(f"asimov.net.110: received {data=} from {src=}")
                packet_type, *_ = decode_packet(data)
                if packet_type == PACKET_TYPE_PONG:
                    return True
            except socket.timeout:
                print(f"asimov.net.120: timeout waiting for PONG (attempt {attempt+1})")
                continue
    finally:
        # Restore original timeout
        sender.sock.settimeout(original_timeout)

    return False

class UDPSender:
    def __init__(self, remote_host, remote_port, local_port=None):
        self.addr = (remote_host, remote_port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.local_port = local_port
        if local_port is not None:
            self.sock.bind(("0.0.0.0", local_port))
        print(f"asimov.net.UDPSender.100: {self.addr=}")

    def __str__(self):
        return f"UDPSender: {self.addr=} {self.local_port=}"

    def receive(self, packetsize=MAX_PACKET_SIZE):
        print("[net] receive() called")
        return self.sock.recvfrom(packetsize)

    def send(self, packet):
        return self.sock.sendto(packet, self.addr)

    def send_ping(self):
        print(f"sending ping...")
        # self.sock.sendto(encode_packet(PACKET_TYPE_PING, 0, 0, 1, b''), self.addr)
        packet = encode_packet(PACKET_TYPE_PING, 0, 0, 1, b'')
        self.send(packet)

    def send_pong(self):
        print(f"[net] PONG")
        packet = encode_packet(PACKET_TYPE_PONG, 0, 0, 1, b'')
        count = self.send(packet)

    def send_eos(self):
        packet = encode_packet(PACKET_TYPE_EOS, 0, 0, 1, b'')
        count = self.send(packet)
        print(f"send_eos {count=}")
        # self.sock.sendto(encode_packet(PACKET_TYPE_EOS, 0, 0, 1, b''), self.addr)

    def send_frame(self, frame):
        encoded, buffer = cv2.imencode(".jpg", frame)
        data = buffer.tobytes()
        frame_id = self.frame_counter
        self.frame_counter += 1

        chunk_size = self.packetsize - HEADER_SIZE
        total_chunks = (len(data) + chunk_size - 1) // chunk_size

        for chunk_id in range(total_chunks):
            start = chunk_id * chunk_size
            end = start + chunk_size
            payload = data[start:end]
            packet = encode_packet(PACKET_TYPE_FRAME, frame_id, chunk_id, total_chunks, payload)
            self.sock.sendto(packet, self.addr)

    def close(self):
        """Close the underlying UDP socket."""
        self.sock.close()


class UDPReceiver:
    def __init__(self, host, port, packetsize=1500, blocking=True):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.addr = (host, port)
        self.sock.bind(self.addr)
        self.sock.setblocking(blocking)
        self.packetsize = packetsize
        self.buffer = {}  # Optional: for frame reassembly
        self.host = host
        self.port = port

    def receive(self, packet_size=MAX_PACKET_SIZE):
        try:
            data, addr = self.sock.recvfrom(packet_size)
            return decode_packet(data)+(addr,)
##            packet_type, frame_id, chunk_id, total_chunks, payload = decode_packet(data)
##            return packet_type, frame_id, chunk_id, payload, addr
        except BlockingIOError:
            return None

    def close(self):
        self.sock.close()
