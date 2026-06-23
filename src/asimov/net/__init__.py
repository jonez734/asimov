# asimov_net/__init__.py
# Network package for Asimov - video frame transmission
# Uses bbsengine6.net for TCP/UDP/socket, has its own videoframe code

# Configuration
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

# Socket utilities from bbsengine6.net
from bbsengine6.net import (
    recv_all,
    recv_udp,
    send_with_length,
    recv_with_length,
)

# TCP sender/receiver from bbsengine6.net
from bbsengine6.net import (
    TCPSender,
    TCPReceiver,
)

from .packet import (
    Packet,
    encode_packet,
    decode_packet,
    register_packet_type,
    NetError,
    PacketTypeError,
    PING,
    PONG,
    EOS,
    PACKET_TYPE_PING,
    PACKET_TYPE_PONG,
    PACKET_TYPE_EOS,
)

# Video frame (asimov-specific)
from .videoframe import (
    FramePacket,
    encode_frame_packet,
    decode_frame_packet,
    PACKET_TYPE_FRAME,
    FRAME_PACKET_HEADER_SIZE,
)

# Video frame types - from bbsengine6.net (general-purpose, not video-specific)
from bbsengine6.net import (
    Frame,
    NumpyFrame,
    frame_from_any,
    frames_equal,
)

# Backward compatibility aliases
VideoFrame = Frame
NumpyVideoFrame = NumpyFrame

# Video frame addressing (asimov-specific)
from .videoframe_address import (
    FrameScheme,
    FrameAddress,
    FrameAddressParser,
    ParseResult,
    default_port_for_scheme,
)

# Ping utilities (asimov-specific)
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
    # socket (from bbsengine6)
    "recv_all",
    "recv_udp",
    "send_with_length",
    "recv_with_length",
    # tcp (from bbsengine6)
    "TCPSender",
    "TCPReceiver",
    # packet
    "Packet",
    "FramePacket",
    "encode_packet",
    "decode_packet",
    "encode_frame_packet",
    "decode_frame_packet",
    "FRAME_PACKET_HEADER_SIZE",
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
    # videoframe_types
    "VideoFrame",
    "NumpyVideoFrame",
    "Frame",  # backward compat
    "NumpyFrame",  # backward compat
    "frame_from_any",
    "frames_equal",
    # videoframe_address
    "FrameScheme",
    "FrameAddress",
    "FrameAddressParser",
    "ParseResult",
    "default_port_for_scheme",
    # ping
    "respond_to_ping",
    "send_ping_and_wait_for_pong",
    "wait_for_pong",
]
