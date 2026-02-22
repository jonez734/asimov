# asimov/net/packet.py
# Packet types, encoding/decoding, and packet classes

import struct
import time
import socket
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

PACKET_TYPE_PING = 1
PACKET_TYPE_PONG = 2
PACKET_TYPE_EOS = 3
PACKET_TYPE_FRAME = 5

_packet_type_registry: Dict[int, type] = {}


class NetError(Exception):
    """Base exception for network errors."""
    pass


class PacketTypeError(NetError):
    """Raised when packet type is unknown."""
    pass


class PING:
    """Sentinel for PING packets."""
    pass


class PONG:
    """Sentinel for PONG packets."""
    pass


class EOS:
    """Sentinel for End-of-Stream packets."""
    pass


def register_packet_type(packet_class):
    """Register a packet class for dynamic decoding."""
    if hasattr(packet_class, 'packet_type'):
        _packet_type_registry[packet_class.packet_type] = packet_class
    return packet_class


def encode_packet(packet_type: int, **kwargs) -> bytes:
    """Encode a packet with given type and fields."""
    if packet_type == PACKET_TYPE_PING:
        payload = struct.pack("!d", time.time())
        return _encode_header(PACKET_TYPE_PING, payload) + payload
    elif packet_type == PACKET_TYPE_PONG:
        orig_ts = kwargs.get('timestamp', time.time())
        payload = struct.pack("!d", orig_ts)
        return _encode_header(PACKET_TYPE_PONG, payload) + payload
    elif packet_type == PACKET_TYPE_EOS:
        payload = b""
        return _encode_header(PACKET_TYPE_EOS, payload) + payload
    else:
        raise PacketTypeError(f"Unknown packet type: {packet_type}")


def _encode_header(packet_type: int, payload: bytes) -> bytes:
    """Encode packet header with type, timestamp, and payload length."""
    timestamp = time.time()
    payload_len = len(payload)
    return struct.pack("!IdI", packet_type, timestamp, payload_len)


def decode_packet(data: bytes) -> Dict[str, Any]:
    """Decode a packet from raw bytes."""
    if len(data) < 16:
        raise NetError("Packet data too short")

    packet_type, timestamp, payload_len = struct.unpack("!IdI", data[:16])
    payload = data[16:16 + payload_len]

    result = {
        'packet_type': packet_type,
        'timestamp': timestamp,
        'payload': payload,
    }

    if packet_type == PACKET_TYPE_PING:
        result['packet_type'] = PING
    elif packet_type == PACKET_TYPE_PONG:
        result['packet_type'] = PONG
    elif packet_type == PACKET_TYPE_EOS:
        result['packet_type'] = EOS

    return result


class Packet:
    """
    Packet with type, payload, timestamp.
    Serialized as: [type (I)][timestamp (d)][payload length (I)][payload]
    """
    def __init__(self, ptype: int, payload: bytes = b"", timestamp: float = 0.0):
        self.ptype = ptype
        self.payload = payload
        self.timestamp = timestamp if timestamp != 0.0 else time.time()

    def encode(self) -> bytes:
        payload_len = len(self.payload)
        header = struct.pack("!IdI", self.ptype, self.timestamp, payload_len)
        return header + self.payload

    @staticmethod
    def decode(data: bytes) -> "Packet":
        if len(data) < 16:
            raise ValueError("Packet data too short")
        ptype, timestamp, payload_len = struct.unpack("!IdI", data[:16])
        payload = data[16:16 + payload_len]
        return Packet(ptype, payload, timestamp)

    @staticmethod
    def recv(sock: socket.socket) -> Optional["Packet"]:
        from .socket import recv_all
        header = recv_all(sock, 16)
        if header is None:
            return None
        ptype, timestamp, payload_len = struct.unpack("!IdI", header)
        payload = recv_all(sock, payload_len)
        if payload is None:
            return None
        return Packet(ptype, payload, timestamp)


# Frame packet header format:
# packet_type (B) + timestamp (d) + frame_id (I) + block_id (I) +
# cols (H) + rows (H) + block_w (H) + block_h (H) + total_blocks (H) +
# is_delta (B) + compressed (B) + blocks_in_packet (H)
# = 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 = 12 items
FRAME_PACKET_HEADER_FORMAT = "!BdIIHHHHHBBH"
FRAME_PACKET_HEADER_SIZE = struct.calcsize(FRAME_PACKET_HEADER_FORMAT)


@dataclass
class FramePacket(Packet):
    """Packet for transmitting frame chunks with delta and batching support."""
    frame_id: int = 0
    block_id: int = 0
    cols: int = 0
    rows: int = 0
    block_w: int = 0
    block_h: int = 0
    total_blocks: int = 0
    is_delta: bool = False
    compressed: bool = False
    blocks: List[bytes] = field(default_factory=list)
    packet_type: int = field(init=False, default=PACKET_TYPE_FRAME)
    timestamp: float = field(default_factory=time.time)
    blocks_in_packet: int = 1

    def __post_init__(self):
        self.packet_type = PACKET_TYPE_FRAME


def encode_frame_header(packet: FramePacket) -> bytes:
    """Encode frame packet header."""
    return struct.pack(
        FRAME_PACKET_HEADER_FORMAT,
        packet.packet_type,
        packet.timestamp,
        packet.frame_id,
        packet.block_id,
        packet.cols,
        packet.rows,
        packet.block_w,
        packet.block_h,
        packet.total_blocks,
        1 if packet.is_delta else 0,
        1 if packet.compressed else 0,
        packet.blocks_in_packet
    )


def encode_frame_packet(packet: FramePacket) -> bytes:
    """Encode frame packet with header and body."""
    header = encode_frame_header(packet)
    body = b''.join(packet.blocks)
    return header + body


def decode_frame_packet(data: bytes) -> FramePacket:
    """Decode frame packet from raw bytes."""
    header_size = FRAME_PACKET_HEADER_SIZE
    header = data[:header_size]
    (
        packet_type,
        timestamp,
        frame_id,
        block_id,
        cols,
        rows,
        block_w,
        block_h,
        total_blocks,
        is_delta_flag,
        compressed_flag,
        blocks_in_packet
    ) = struct.unpack(FRAME_PACKET_HEADER_FORMAT, header)

    blocks = []
    offset = header_size
    block_data_len = len(data[header_size:]) // blocks_in_packet if blocks_in_packet > 0 else 0
    
    for _ in range(blocks_in_packet):
        if offset + block_data_len <= len(data):
            block = data[offset:offset + block_data_len]
            blocks.append(block)
            offset += block_data_len

    return FramePacket(
        frame_id=frame_id,
        block_id=block_id,
        cols=cols,
        rows=rows,
        block_w=block_w,
        block_h=block_h,
        total_blocks=total_blocks,
        is_delta=bool(is_delta_flag),
        compressed=bool(compressed_flag),
        blocks=blocks,
        timestamp=timestamp,
        blocks_in_packet=blocks_in_packet
    )
