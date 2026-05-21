# asimov_net Specification

## Overview

`asimov_net` is a networking library for Asimov that provides TCP/UDP frame transmission capabilities with RFC 3986 DSN-style addressing. It enables sending and receiving video frames over network sockets with support for delta compression, chunking, batching, and flexible constructor APIs.

## Package Structure

```
asimov_net/
├── __init__.py           # Public API exports (57 items)
├── conf.py               # Configuration constants
├── socket.py             # Low-level socket utilities
├── packet.py             # Base packet types and encoding
├── frame.py              # Frame packet types and encoding
├── frame_types.py        # Frame type abstractions (bytes/numpy) - NEW
├── frame_address.py      # RFC 3986 DSN-style frame addressing - NEW
├── tcp.py                # TCP sender/receiver with DSN support - ENHANCED
├── udp.py                # UDP sender/receiver with DSN support - ENHANCED
└── ping.py               # Ping/Pong utilities
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

### frame_types.py (NEW)

Frame type abstractions supporting both raw bytes and NumPy arrays:

**Classes:**
- `Frame` - Wraps raw bytes with dimensions
  - `__init__(data: bytes, width: int, height: int)`
  - `to_bytes() -> bytes` - Get raw bytes
  - `shape -> Tuple[int, int]` - (height, width)

- `NumpyFrame` - Wraps NumPy array (optional numpy dependency)
  - `__init__(array: np.ndarray)`
  - `to_bytes() -> bytes` - Convert to bytes
  - `to_numpy() -> np.ndarray` - Get NumPy array

**Functions:**
- `frame_from_any(data, width: int, height: int) -> Frame` - Create Frame from bytes or numpy
- `frames_equal(frame1: Frame, frame2: Frame) -> bool` - Compare frames with tolerance

**Features:**
- Optional numpy dependency (graceful fallback to bytes)
- Transparent conversion between formats
- Dimension preservation

### frame_address.py (NEW)

RFC 3986 compliant DSN-style addressing for frame transmission:

**Enums:**
- `FrameScheme` - `tcp`, `udp`, `unix`, `ws`, `wss`

**Classes:**
- `FrameAddress` - Parsed frame address
  - Fields: `scheme`, `host`, `port`, `path`, `query_params`
  - Properties: `uri`, `netloc`

- `FrameAddressParser` - Parser for frame URIs
  - `parse(uri: str) -> ParseResult[FrameAddress]`
  - Supports schemes: `tcp://`, `udp://`, `unix://`, `ws://`, `wss://`
  - Standard parameters: `timeout`, `retry`, `keepalive`, `backoff`
  - Custom parameter support

- `ParseResult[T]` - Result object for error handling
  - `success: bool` - Parse succeeded
  - `value: T` - Parsed value (if success)
  - `error: str` - Error message (if not success)

**Functions:**
- `default_port_for_scheme(scheme: FrameScheme) -> int` - Get default port for scheme

**Examples:**
```python
parser = FrameAddressParser()

# Basic TCP address
result = parser.parse("tcp://192.168.1.100:5000")
assert result.success
assert result.value.host == "192.168.1.100"
assert result.value.port == 5000

# UDP with parameters
result = parser.parse("udp://host.example.com:6000?timeout=30&retry=5")
assert result.value.query_params["timeout"] == "30"

# Unix socket
result = parser.parse("unix:///tmp/video.sock")
assert result.value.scheme == FrameScheme.unix
```

### tcp.py (ENHANCED)

TCP-based frame transmission with flexible constructor and DSN support:

**Classes:**

`TCPSender`
- **Multiple constructor patterns:**
  ```python
  # Old style (backward compatible)
  TCPSender("host", 5000)
  
  # DSN style
  TCPSender("tcp://host:5000?timeout=30")
  
  # Address object
  TCPSender(address=FrameAddress(...))
  ```
- `connect()` - Establish TCP connection
- `send(packet: Packet)` - Send generic packet
- `send_frame(frame, frame_id, prev_frame=None, cols=0, rows=0, compress=False, full_frame=False, auto_batch=True)` - Send video frame
- `recv() -> Optional[Packet]` - Receive packet
- `close()` - Close connection

`TCPReceiver`
- **Multiple constructor patterns (same as TCPSender)**
- `receive() -> Optional[FramePacket]` - Receive frame packet
- `close()` - Close connection

**Features:**
- Backward compatible with old API: `TCPSender("host", port)`
- New DSN API: `TCPSender("tcp://host:port?timeout=30")`
- Delta frame transmission (only changed blocks)
- Automatic block batching to fill packets
- Optional zlib compression
- Configurable grid dimensions for block partitioning

### udp.py (ENHANCED)

UDP-based frame transmission with flexible constructor and optional numpy:

**Constants:**
- `UDP_MAX_PAYLOAD` - Maximum UDP payload size

**Classes:**

`UDPSender`
- **Multiple constructor patterns (same as TCPSender)**
- `send_frame(...)` - Send video frame (same interface as TCPSender)
- `send_ping()` - Send PING packet
- `send_pong(timestamp=0.0)` - Send PONG packet
- `send_eos()` - Send End-of-Stream packet
- `receive(timeout=0.5) -> Optional[dict]` - Receive packet (non-blocking)
- `close()` - Close socket

`UDPReceiver`
- **Multiple constructor patterns**
- `start_listening()` - Start listening loop
- `receive() -> Any` - Receive and process packets
- `close()` - Close socket

**Features:**
- Frame reassembly from multiple packets
- Delta frame support
- Optional zlib compression
- Callback-based frame delivery
- Non-blocking mode support
- Works with raw bytes OR numpy arrays (optional dependency)

### ping.py

Ping/Pong utilities for connection testing:

| Function | Signature | Description |
|----------|-----------|-------------|
| `respond_to_ping` | `(sock, addr)` | Send PONG response to PING |
| `send_ping_and_wait_for_pong` | `(sock, timeout=1.0) -> bool` | Send PING and wait for response |
| `wait_for_pong` | `(sock, timeout=1.0) -> Optional[dict]` | Wait for PONG response |

## Protocol Specification

### Packet Header Format

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

## DSN Address Specification

Frame addresses follow RFC 3986 URI syntax:

```
scheme://[user:password@]host[:port][/path][?query_string]
```

**Supported Schemes:**
- `tcp://` - TCP socket (default port: 5000)
- `udp://` - UDP socket (default port: 5000)
- `unix://` - Unix domain socket
- `ws://` - WebSocket (default port: 80)
- `wss://` - Secure WebSocket (default port: 443)

**Standard Query Parameters:**
- `timeout` - Socket timeout in seconds
- `retry` - Number of connection retries
- `keepalive` - Keep-alive setting
- `backoff` - Backoff strategy for retries

**Examples:**
```
tcp://192.168.1.100:5000
tcp://video-server.example.com:6000?timeout=30&retry=5
udp://127.0.0.1:5000?keepalive=true
unix:///tmp/video.sock
```

## Usage Examples

### Frame Transmission (Old API - Backward Compatible)

```python
from asimov.net import TCPSender, TCPReceiver

# Sender
sender = TCPSender("127.0.0.1", 6000)
sender.connect()
sender.send_frame(frame, frame_id=1)

# Receiver
receiver = TCPReceiver("127.0.0.1", 6000)
packet = receiver.receive()
```

### Frame Transmission (New DSN API)

```python
from asimov.net import TCPSender, TCPReceiver

# Sender with timeout
sender = TCPSender("tcp://video-server.com:6000?timeout=30&retry=5")
sender.connect()
sender.send_frame(frame, frame_id=1)

# Receiver with DSN
receiver = TCPReceiver("tcp://127.0.0.1:6000")
packet = receiver.receive()
```

### Frame Type Handling

```python
from asimov.net import Frame, NumpyFrame, frame_from_any

# Create frame from bytes
frame = Frame(bytes_data, width=640, height=480)

# Create from numpy (if available)
import numpy as np
array = np.zeros((480, 640, 3), dtype=np.uint8)
frame = frame_from_any(array, 640, 480)

# Convert between formats
frame_bytes = frame.to_bytes()
```

### Frame Address Parsing

```python
from asimov.net import FrameAddressParser

parser = FrameAddressParser()

# Parse DSN address
result = parser.parse("tcp://192.168.1.100:5000?timeout=30")
if result.success:
    addr = result.value
    print(f"Host: {addr.host}, Port: {addr.port}")
else:
    print(f"Parse error: {result.error}")
```

### UDP Frame Transmission

```python
from asimov.net import UDPSender, UDPReceiver

# Sender
sender = UDPSender("udp://127.0.0.1:6000")
sender.send_frame(frame, frame_id=1)

# Receiver with callback
def on_frame(frame, frame_id):
    process(frame)

receiver = UDPReceiver("udp://127.0.0.1:6000", frame_received_callback=on_frame)
receiver.start_listening()
```

### Ping/Pong

```python
from asimov.net import UDPSender

sender = UDPSender("udp://127.0.0.1:6000")
sender.send_ping()
response = sender.receive()
```

## Dependencies

### Core Dependencies
- `stdlib` - No external dependencies for core frame transmission

### Optional Dependencies
- `numpy` - For NumpyFrame type (graceful fallback if not available)

## Backward Compatibility

All changes are fully backward compatible:
- Old constructor patterns work unchanged
- New DSN API is additive, not replacing
- Frame handling works with both bytes and numpy arrays

## Changes from BBSEngine6 Consolidation

This package now contains all video frame transmission code previously in `bbsengine6.net`:
- Added `frame_types.py` for flexible frame handling
- Added `frame_address.py` for RFC 3986 DSN addressing
- Enhanced `tcp.py` and `udp.py` with flexible constructors
- Established asimov as canonical source for frame transmission
- Allows bbsengine6 to focus on notification infrastructure
