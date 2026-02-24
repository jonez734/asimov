# asimov_net Specification

## Overview

`asimov_net` is a package for TCP/UDP network communication and cv2 frame transmission. It provides socket helpers, packet encoding/decoding, and client/server classes for sending and receiving video frames over the network.

## Architecture

```
asimov_net/
├── __init__.py    # Re-exports all symbols
├── conf.py        # Configuration constants
├── socket.py      # Low-level socket helpers
├── packet.py      # Packet classes and encoding
├── tcp.py         # TCP sender/receiver
├── udp.py         # UDP sender/receiver with frame support
└── ping.py        # Ping/pong utilities
```

## Configuration (conf.py)

Configuration constants for network communication. Some values are imported from `asimov.conf`.

```python
from asimov_net import (
    CHUNK_SIZE,           # Block size for frame chunking (default: 64)
    DEFAULT_PORT,         # Default network port (default: 5000)
    COMPRESSION_ENABLED,  # Enable zlib compression (default: False)
    BUFFER_SIZE,         # UDP buffer size (default: 65507)
    
    # Pipeline host/port configuration
    VIDEOCAPTURE_HOST,   # Videocapture stage host
    VIDEOCAPTURE_PORT,   # Videocapture stage port
    PROCESSING_HOST,      # Processing stage host
    PROCESSING_PORT,      # Processing stage port
    RENDER_HOST,         # Render stage host
    RENDER_PORT,         # Render stage port
    
    # Buffer sizes
    TCP_BUFFER_SIZE,     # TCP buffer size (default: 8192)
    UDP_BUFFER_SIZE,     # UDP buffer size (default: 65507)
    
    # Retry configuration
    RETRY_DELAY,         # Retry delay in seconds (default: 0.2)
    RETRY_COUNT,         # Number of retries (default: 5)
    
    # Capture defaults (imported from asimov.conf)
    CAPTURE_WIDTH,       # Default capture width (from conf)
    CAPTURE_HEIGHT,      # Default capture height (from conf)
    CAPTURE_FPS,         # Default capture FPS (from conf)
    CAPTURE_DEVICE,      # Default capture device (from conf)
)
```

## Socket Helpers (socket.py)

Low-level socket utilities for TCP/UDP communication.

```python
def recv_all(sock: socket.socket, length: int) -> Optional[bytes]:
    """Receive exactly `length` bytes from a TCP socket, or None if closed."""

def recv_udp(sock: socket.socket, bufsize: int = 4096) -> Tuple[Optional[bytes], Optional[Tuple[str, int]]]:
    """Receive a single datagram from a UDP socket."""

def send_with_length(conn: socket.socket, payload: bytes):
    """Send a length-prefixed payload (4-byte big-endian length + data)."""

def recv_with_length(conn: socket.socket) -> bytes:
    """Receive a length-prefixed payload."""

def retry_until_connected(host: str, port: int, retries: int = 5, delay: float = 0.2) -> socket.socket:
    """Connect with retries, returning a connected socket or raising the last exception."""
```

## Packet Types and Encoding (packet.py)

### Constants

```python
PACKET_TYPE_PING = 1     # Connection test request
PACKET_TYPE_PONG = 2     # Connection test response
PACKET_TYPE_EOS = 3      # End-of-stream signal
PACKET_TYPE_FRAME = 5    # Frame data packet
```

### Sentinels

```python
PING  # Sentinel for PING packets
PONG  # Sentinel for PONG packets
EOS   # Sentinel for End-of-Stream packets
```

### Exceptions

```python
class NetError(Exception):
    """Base exception for network errors."""

class PacketTypeError(NetError):
    """Raised when packet type is unknown."""
```

### Packet Classes

```python
class Packet:
    """General packet with type, payload, and timestamp."""
    def __init__(self, ptype: int, payload: bytes = b"", timestamp: float = None)
    def encode(self) -> bytes
    @staticmethod
    def decode(data: bytes) -> "Packet"
    @staticmethod
    def recv(sock: socket.socket) -> Optional["Packet"]

@dataclass
class FramePacket(Packet):
    """Packet for transmitting frame chunks."""
    frame_id: int
    block_id: int
    block_data_len: int
    compressed: bool
    blocks: List[bytes]
    packet_type: int = PACKET_TYPE_FRAME
    timestamp: float = field(default_factory=time.time)
    blocks_in_packet: int = 1
    total_blocks_in_frame: int = 1
```

### Encoding/Decoding Functions

```python
def encode_packet(packet_type: int, **kwargs) -> bytes:
    """Encode a PING, PONG, or EOS packet."""

def decode_packet(data: bytes) -> Dict[str, Any]:
    """Decode a packet, returning dict with packet_type (or sentinel), timestamp, payload."""

def encode_frame_packet(packet: FramePacket) -> bytes:
    """Encode a FramePacket for transmission."""

def decode_frame_packet(data: bytes) -> FramePacket:
    """Decode a FramePacket from raw bytes."""

def register_packet_type(packet_class):
    """Register a packet class for dynamic decoding."""
```

## TCP Classes (tcp.py)

```python
class TCPSender:
    """TCP client for sending packets."""
    def __init__(self, host: str, port: int)
    def connect(self)
    def send(self, packet: Packet)
    def recv(self) -> Optional[Packet]
    def close(self)

class TCPReceiver:
    """TCP server for receiving packets."""
    def __init__(self, sock: socket.socket)
    def recv(self) -> Optional[Packet]
```

## UDP Classes (udp.py)

UDP sender and receiver with built-in frame chunking and reassembly.

```python
class UDPSender:
    """UDP sender with frame chunking support."""
    def __init__(
        self,
        host: str,
        port: int,
        bind_port: int = 0,
        blocking: bool = False
    )
    
    def send_frame(
        self,
        frame: np.ndarray,
        frame_id: int,
        block_size: int = CHUNK_SIZE,
        compress: bool = False
    ):
        """Send a frame as chunks."""
    
    def send_ping(self):
        """Send a PING packet."""
    
    def send_pong(self, timestamp: float = None):
        """Send a PONG packet."""
    
    def send_eos(self):
        """Send an End-of-Stream packet."""
    
    def receive(self, timeout: float = 0.5) -> Optional[dict]:
        """Receive a packet (non-blocking)."""
    
    def close(self)


class UDPReceiver:
    """UDP receiver with frame reassembly."""
    def __init__(
        self,
        host: str,
        port: int,
        frame_received_callback: Optional[Callable] = None,
        idle_callback: Optional[Callable] = None,
        local_port: int = 0,
        blocking: bool = True,
        timeout: float = 0.5,
        block_size: int = CHUNK_SIZE,
        compress: bool = False
    )
    
    def start_listening(self):
        """Start listening for frames in a loop."""
    
    def receive(self) -> Any:
        """Receive and reassemble frames. Returns frame, PING, PONG, EOS, or None."""
    
    def close(self):
```

### Frame Transmission Details

Frames are split into square blocks for transmission:

1. Frame is divided into `block_size x block_size` chunks
2. Each chunk is optionally compressed with zlib
3. Chunks are sent as `FramePacket` with metadata:
   - `frame_id`: Unique frame identifier
   - `block_id`: Chunk index within frame
   - `total_blocks_in_frame`: Total chunks in frame
   - `compressed`: Whether data is zlib-compressed
4. Receiver reassembles chunks into full frame

## Ping/Pong Utilities (ping.py)

```python
def respond_to_ping(sock: socket.socket, addr: tuple):
    """Send a PONG response to a PING sender."""

def send_ping_and_wait_for_pong(sock: socket.socket, timeout: float = 1.0) -> bool:
    """Send PING and wait for PONG. Returns True if PONG received, False on timeout."""

def wait_for_pong(sock: socket.socket, timeout: float = 1.0) -> Optional[dict]:
    """Wait for a PONG response with timeout."""
```

## Capture Configuration (asimov/util.py)

For configuring video capture, use `asimov.util.configure_capture`:

```python
from asimov import util

def configure_capture(
    cap: cv2.VideoCapture,
    width: Optional[int] = None,
    height: Optional[int] = None,
    fps: Optional[int] = None,
) -> Optional[Tuple[int, int, int]]:
    """
    Configure video capture properties and return actual values.
    
    Args:
        cap: OpenCV VideoCapture object
        width: Desired frame width (None = don't set)
        height: Desired frame height (None = don't set)
        fps: Desired FPS (None = don't set)
    
    Returns:
        Tuple of (actual_width, actual_height, actual_fps) on success
        None if capture is not open
    """
```

## Usage Examples

### Best Practices

- **Default host**: Always use `127.0.0.1` as the default host, never `0.0.0.0`
  - `0.0.0.0` means "all interfaces" and is for server binding
  - `127.0.0.1` is local-only and more secure for demos/cli tools
- **Ports**: Use port 5000 as default for demos
- **Delta frames**: Enable by default for bandwidth efficiency
- **Auto-batching**: Enabled by default to maximize packet efficiency

### UDP Frame Sender

```python
from asimov_net import UDPSender
from asimov import util
import cv2

sender = UDPSender("127.0.0.1", 5000)
cap = cv2.VideoCapture(0)

result = util.configure_capture(cap, width=640, height=480, fps=30)
if result is None:
    print("Failed to configure capture")
    exit(1)

actual_width, actual_height, actual_fps = result
print(f"Capturing at {actual_width}x{actual_height} @ {actual_fps} FPS")

frame_id = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    sender.send_frame(frame, frame_id, block_size=64, compress=False)
    frame_id += 1

sender.close()
cap.release()
```

### UDP Frame Receiver

```python
from asimov_net import UDPReceiver
import cv2

receiver = UDPReceiver("127.0.0.1", 5000, blocking=False, timeout=1.0)

while True:
    result = receiver.receive()
    
    if result is None:
        continue
    
    if hasattr(result, 'frame_id'):
        frame = result  # Complete reassembled frame
        cv2.imshow("Received", frame)
        if cv2.waitKey(1) == ord('q'):
            break
    elif result == receiver.EOS:
        print("Stream ended")
        break

receiver.close()
cv2.destroyAllWindows()
```

### Ping/Pong Handshake

```python
from asimov_net import UDPSender, UDPReceiver, send_ping_and_wait_for_pong

# Server: respond to pings
server = UDPReceiver("127.0.0.1", 5000)
while True:
    result = server.receive()
    if result == PING:
        server.send_pong()

# Client: send ping, wait for pong
client = UDPSender("127.0.0.1", 5000)
if send_ping_and_wait_for_pong(client):
    print("Connection OK")
else:
    print("No response")
```
