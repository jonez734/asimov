# asimov/net/__init__.py
# Network package for Asimov - TCP/UDP frame transmission

from .conf import (
    CHUNK_SIZE,
    DEFAULT_PORT,
    COMPRESSION_ENABLED,
    BUFFER_SIZE,
    VIDEOCAPTURE_HOST,
    VIDEOCAPTURE_PORT,
    PROCESSING_HOST,
    PROCESSING_PORT,
    RENDER_HOST,
    RENDER_PORT,
    TCP_BUFFER_SIZE,
    UDP_BUFFER_SIZE,
    RETRY_DELAY,
    RETRY_COUNT,
    CAPTURE_WIDTH,
    CAPTURE_HEIGHT,
    CAPTURE_FPS,
    CAPTURE_DEVICE,
)

from .socket import (
    recv_all,
    recv_udp,
    send_with_length,
    recv_with_length,
    retry_until_connected,
)

from .packet import (
    Packet,
    FramePacket,
    encode_packet,
    decode_packet,
    encode_frame_packet,
    decode_frame_packet,
    register_packet_type,
    NetError,
    PacketTypeError,
    PING,
    PONG,
    EOS,
    PACKET_TYPE_PING,
    PACKET_TYPE_PONG,
    PACKET_TYPE_EOS,
    PACKET_TYPE_FRAME,
)

from .tcp import (
    TCPSender,
    TCPReceiver,
)

from .udp import (
    UDPSender,
    UDPReceiver,
    UDP_MAX_PAYLOAD,
)

from .ping import (
    respond_to_ping,
    send_ping_and_wait_for_pong,
    wait_for_pong,
)

__all__ = [
    # conf
    "CHUNK_SIZE",
    "DEFAULT_PORT", 
    "COMPRESSION_ENABLED",
    "BUFFER_SIZE",
    "VIDEOCAPTURE_HOST",
    "VIDEOCAPTURE_PORT",
    "PROCESSING_HOST",
    "PROCESSING_PORT",
    "RENDER_HOST",
    "RENDER_PORT",
    "TCP_BUFFER_SIZE",
    "UDP_BUFFER_SIZE",
    "RETRY_DELAY",
    "RETRY_COUNT",
    "CAPTURE_WIDTH",
    "CAPTURE_HEIGHT",
    "CAPTURE_FPS",
    "CAPTURE_DEVICE",
    # socket
    "recv_all",
    "recv_udp", 
    "send_with_length",
    "recv_with_length",
    "retry_until_connected",
    # packet
    "Packet",
    "FramePacket",
    "encode_packet",
    "decode_packet",
    "encode_frame_packet",
    "decode_frame_packet",
    "register_packet_type",
    "NetError",
    "PacketTypeError",
    "PING",
    "PONG",
    "EOS",
    "PACKET_TYPE_PING",
    "PACKET_TYPE_PONG",
    "PACKET_TYPE_EOS",
    "PACKET_TYPE_FRAME",
    # tcp
    "TCPSender",
    "TCPReceiver",
    # udp
    "UDPSender",
    "UDPReceiver",
    "UDP_MAX_PAYLOAD",
    # ping
    "respond_to_ping",
    "send_ping_and_wait_for_pong",
    "wait_for_pong",
]
