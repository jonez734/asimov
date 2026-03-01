# asimov_net Specification

## Overview

`asimov_net` is a networking library for Asimov that provides TCP/UDP frame transmission capabilities. It enables sending and receiving video frames over network sockets with support for delta compression, chunking, and batching.

## Package Structure

```
asimov_net/
├── __init__.py      # Public API exports
├── conf.py          # Configuration constants
├── socket.py        # Low-level socket utilities
├── packet.py        # Base packet types and encoding
├── frame.py         # Frame packet types and encoding
├── tcp.py           # TCP sender/receiver classes
├── udp.py           # UDP sender/receiver classes
└── ping.py          # Ping/Pong utilities
```

## Module Specifications

### conf.py

Configuration constants for the networking package:

| Constant | Type | Default | Description |
|----------|------|---------|-------------|
| `CHUNK_SIZE` | int | 64 | Chunk size for data splitting |
| `DEFAULT_PORT` | int | 5000 | Default network port |
| `COMPRESSION_ENABLED` | bool | False | Enable zlib compression |
| `BUFFER_SIZE` | int | 65507 | UDP buffer size |
| `TCP_BUFFER_SIZE` | int | 8192 | TCP buffer size |
| `UDP_BUFFER_SIZE` | int | 65507 | UDP buffer size |
| `RETRY_DELAY` | float | 0.2 | Delay between connection retries |
| `RETRY_COUNT` | int | 5 | Number of connection retries |
| `VIDEOCAPTURE_HOST` | str | "127.0.0.1" | Video capture service host |
| `VIDEOCAPTURE_PORT` | int | 5000 | Video capture service port |
| `PROCESSING_HOST` | str | "127.0.0.1" | Processing service host |
| `PROCESSING_PORT` | int | 6000 | Processing service port |
| `RENDER_HOST` | str | "127.0.0.1" | Render service host |
| `RENDER_PORT` | int | 6000 | Render service port |
| `CAPTURE_WIDTH` | int | (from base) | Capture frame width |
| `CAPTURE_HEIGHT` | int | (from base) | Capture frame height |
| `CAPTURE_FPS` | int | (from base) | Capture frames per second |
| `CAPTURE_DEVICE` | int | (from base) | Capture device index |

### socket.py

Low-level socket helper functions:

| Function | Signature | Description |
|----------|-----------|-------------|
| `recv_all` | `(sock, length) -> Optional[bytes]` | Receive exactly `length` bytes from TCP socket |
| `recv_udp` | `(sock, bufsize=4096) -> Tuple[Optional[bytes], Optional[Tuple[str, int]]]` | Receive single datagram from UDP socket |
| `send_with_length` | `(conn, payload)` | Send length-prefixed payload (4-byte big-endian length + data) |
| `recv_with_length` | `(conn) -> bytes` | Receive length-prefixed payload |
| `retry_until_connected` | `(host, port, retries=5, delay=0.2) -> socket.socket` | Retry TCP connection with backoff |

### packet.py

Base packet types and encoding/decoding:

**Packet Types:**
- `PACKET_TYPE_PING = 1` - Ping request
- `PACKET_TYPE_PONG = 2` - Ping response
- `PACKET_TYPE_EOS = 3` - End of stream

**Classes:**
- `NetError` - Base exception for network errors
- `PacketTypeError` - Raised when packet type is unknown
- `Packet` - Generic packet with type, payload, timestamp
  - Serialized format: `[type (I)][timestamp (d)][payload length (I)][payload]`
- `PING`, `PONG`, `EOS` - Sentinel classes for packet type identification

**Functions:**
- `encode_packet(packet_type, **kwargs) -> bytes` - Encode packet with type and fields
- `decode_packet(data: bytes) -> Dict[str, Any]` - Decode packet from raw bytes
- `register_packet_type(packet_class)` - Register packet class for dynamic decoding

### frame.py

Frame-specific packet types for video transmission:

**Constants:**
- `PACKET_TYPE_FRAME = 5` - Frame packet type
- `FRAME_PACKET_HEADER_FORMAT = "!BdIIHHHHHHHBBHB"` - Struct format string
- `FRAME_PACKET_HEADER_SIZE` - Size of header in bytes

**Classes:**
- `FramePacket(Packet)` - Dataclass for frame chunks with delta and batching support
  - Fields: `frame_id`, `block_id`, `cols`, `rows`, `block_w`, `block_h`, `width`, `height`, `total_blocks`, `is_delta`, `compressed`, `blocks`, `timestamp`, `blocks_in_packet`, `block_sizes`

**Functions:**
- `encode_frame_header(packet: FramePacket) -> bytes` - Encode frame packet header
- `encode_frame_packet(packet: FramePacket) -> bytes` - Encode full frame packet with header and body
- `decode_frame_packet(data: bytes) -> FramePacket` - Decode frame packet from raw bytes

### tcp.py

TCP-based frame transmission:

**Classes:**

`TCPSender`
- `__init__(host: str, port: int)` - Initialize sender
- `connect()` - Establish TCP connection
- `send(packet: Packet)` - Send generic packet
- `send_frame(frame, frame_id, prev_frame=None, cols=0, rows=0, compress=False, full_frame=False, auto_batch=True)` - Send video frame
- `recv() -> Optional[Packet]` - Receive packet
- `close()` - Close connection

`TCPReceiver`
- `__init__(host="127.0.0.1", port=5000, blocking=False, timeout=1.0)` - Initialize receiver
- `receive() -> Optional[FramePacket]` - Receive frame packet
- `close()` - Close connection

**Features:**
- Delta frame transmission (only changed blocks)
- Automatic block batching to fill packets
- Optional zlib compression
- Configurable grid dimensions for block partitioning

### udp.py

UDP-based frame transmission:

**Constants:**
- `UDP_MAX_PAYLOAD` - Maximum UDP payload size

**Classes:**

`UDPSender`
- `__init__(host: str, port: int, bind_port=0, blocking=False)` - Initialize sender
- `send_frame(...)` - Send video frame (same interface as TCPSender)
- `send_ping()` - Send PING packet
- `send_pong(timestamp=0.0)` - Send PONG packet
- `send_eos()` - Send End-of-Stream packet
- `receive(timeout=0.5) -> Optional[dict]` - Receive packet (non-blocking)
- `close()` - Close socket

`UDPReceiver`
- `__init__(host: str, port: int, frame_received_callback=None, idle_callback=None, local_port=0, blocking=True, timeout=0.5)` - Initialize receiver
- `start_listening()` - Start listening loop
- `receive() -> Any` - Receive and process packets
- `close()` - Close socket

**Features:**
- Frame reassembly from multiple packets
- Delta frame support
- Optional zlib compression
- Callback-based frame delivery
- Non-blocking mode support

### ping.py

Ping/Pong utilities for connection testing:

| Function | Signature | Description |
|----------|-----------|-------------|
| `respond_to_ping` | `(sock, addr)` | Send PONG response to PING |
| `send_ping_and_wait_for_pong` | `(sock, timeout=1.0) -> bool` | Send PING and wait for response |
| `wait_for_pong` | `(sock, timeout=1.0) -> Optional[dict]` | Wait for PONG response |

## Protocol Specification

### Packet Header packet Format

Base (16 bytes):
```
[packet_type: 4 bytes][timestamp: 8 bytes][payload_length: 4 bytes][payload: variable]
```

Frame packet header (26 bytes):
```
[packet_type: 1 byte][timestamp: 8 bytes]
[frame_id: 4 bytes][block_id: 4 bytes]
[cols: 2 bytes][rows: 2 bytes]
[block_w: 2 bytes][block_h: 2 bytes]
[width: 2 bytes][height: 2 bytes]
[total_blocks: 4 bytes]
[flags: 1 byte][compressed: 1 byte]
[blocks_in_packet: 1 byte][has_block_sizes: 1 byte]
```

### Frame Transmission Flow

1. Frame is divided into blocks based on grid dimensions (cols × rows)
2. Changed blocks are detected using delta comparison (if enabled)
3. Blocks are optionally compressed with zlib
4. Blocks are batched into packets (auto-batching fills packets optimally)
5. Each packet is sent with metadata for reassembly

### Connection Architecture

```
VideoCapture -> TCPSender/UDPSender -> Network -> TCPReceiver/UDPReceiver -> Processing
                                              |
                                              v
                                         UDPReceiver can respond to PING/PONG
```

## Usage Examples

### TCP Frame Transmission

```python
from asimov_net import TCPSender, TCPReceiver

# Sender
sender = TCPSender("127.0.0.1", 6000)
sender.connect()
sender.send_frame(frame, frame_id=1)

# Receiver
receiver = TCPReceiver("127.0.0.1", 6000)
packet = receiver.receive()
```

### UDP Frame Transmission

```python
from asimov_net import UDPSender, UDPReceiver

# Sender
sender = UDPSender("127.0.0.1", 6000)
sender.send_frame(frame, frame_id=1)

# Receiver with callback
def on_frame(frame, frame_id):
    process(frame)

receiver = UDPReceiver("127.0.0.1", 6000, frame_received_callback=on_frame)
receiver.start_listening()
```

### Ping/Pong

```python
from asimov_net import UDPSender

sender = UDPSender("127.0.0.1", 6000)
sender.send_ping()
response = sender.receive()
```
