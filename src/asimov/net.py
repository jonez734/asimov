# asimov/net.py
import socket
import struct
import cv2
import numpy as np

# Packet types
PACKET_TYPE_PING = 1
PACKET_TYPE_PONG = 2
PACKET_TYPE_EOS = 3
PACKET_TYPE_FRAME = 4

# New header format with frame_id (4 bytes)
HEADER_FORMAT = "!BIHHH"  # packet_type (1), frame_id (4), chunk_id (2), total_chunks (2), payload_size (2)
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

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
    Sends a PING to the destination set in the UDPSender and waits for a PONG reply.

    Parameters:
        sender (UDPSender): The configured UDPSender instance.
        timeout (float): Timeout in seconds to wait for each PONG attempt.
        retry (int): Number of times to retry sending a PING.
        packetsize (int): Maximum size of a UDP packet to receive.

    Returns:
        bool: True if a PONG is received within the retry limit, False otherwise.
    """
    sender.sock.settimeout(timeout)

    try:
        print(f"asimov.net.100: {sender.addr=}")
        for attempt in range(retry):
            # Send the PING packet
            packet = encode_packet(PACKET_TYPE_PING, frame_id=0, chunk_id=0, total_chunks=1, payload=b'')
            sender.sock.sendto(packet, sender.addr)

            try:
                # Wait for a reply on the same socket
                data, src = sender.sock.recvfrom(packetsize)
                print(f"{data=} {src=}")
                packet_type, *_ = decode_packet(data)
                if packet_type == PACKET_TYPE_PONG:
                    return True
            except socket.timeout:
                continue  # retry

    finally:
        sender.sock.settimeout(None)  # reset to blocking mode

    return False

class UDPSender:
    def __init__(self, host, port, packetsize=1500, bind_port=None):
        self.addr = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if bind_port is not None:
            self.sock.bind(("0.0.0.0", bind_port))
        self.packetsize = packetsize

    def send_ping(self):
        self.sock.sendto(encode_packet(PACKET_TYPE_PING, 0, 0, 1, b''), self.addr)

    def send_pong(self):
        self.sock.sendto(encode_packet(PACKET_TYPE_PONG, 0, 0, 1, b''), self.addr)

    def send_eos(self):
        self.sock.sendto(encode_packet(PACKET_TYPE_EOS, 0, 0, 1, b''), self.addr)

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
    def __init__(self, port: int, *, bind_ip: str = '0.0.0.0', packetsize: int = 1500):
        self.bind_ip = bind_ip
        self.port = port
##        self.addr = (bind_ip, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.bind_ip, self.port))
        self.buffer = {}  # key: (src, frame_id), value: list of chunks
        self.packetsize = packetsize

    def receive(self):
        data, src = self.sock.recvfrom(self.packetsize)
        packet_type, frame_id, chunk_id, total_chunks, payload = decode_packet(data)

        if packet_type in (PACKET_TYPE_PING, PACKET_TYPE_PONG, PACKET_TYPE_EOS):
            return packet_type, src, None

        elif packet_type == PACKET_TYPE_FRAME:
            key = (src, frame_id)
            if key not in self.buffer:
                self.buffer[key] = [None] * total_chunks

            self.buffer[key][chunk_id] = payload

            if all(chunk is not None for chunk in self.buffer[key]):
                full_data = b''.join(self.buffer.pop(key))
                frame = cv2.imdecode(np.frombuffer(full_data, dtype=np.uint8), cv2.IMREAD_COLOR)
                return PACKET_TYPE_FRAME, src, frame

        return None, None, None

    def close(self):
        """Close the underlying UDP socket."""
        self.sock.close()
