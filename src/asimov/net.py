# net.py
import math
import struct
import socket
import time
from typing import Dict, Any, Type, Callable, Optional
from abc import ABC, abstractmethod
import numpy as np
import cv2

# --- Packet Type Constants ---
PING = 1
PONG = 2
FRAME = 3  # For future extension

PACKET_TYPE_MAP = {
    PING: "PING",
    PONG: "PONG",
    FRAME: "FRAME",
}

# --- Custom Exception ---
class NetError(Exception):
    """Custom exception for network-related errors."""
    pass

# --- Base Packet Class for Extensibility ---
class Packet(ABC):
    """Base class for all network packets.
    Subclasses must define packet_type and implement to_payload_bytes/from_payload_bytes.
    """
    packet_type: int = 0 # To be overridden by subclasses

    @abstractmethod
    def to_payload_bytes(self) -> bytes:
        """Converts the packet's specific data into raw bytes for the payload."""
        pass

    @classmethod
    @abstractmethod
    def from_payload_bytes(cls, payload_data: bytes) -> 'Packet':
        """Creates a packet object from raw payload bytes."""
        pass

    def __repr__(self) -> str:
        # For representation, we might still represent internal data as Python types
        # but the actual wire format is bytes.
        return f"{self.__class__.__name__}(type={self.packet_type}, payload_len={len(self.to_payload_bytes())})"


# --- Specific Packet Implementations ---

class PingPacket(Packet):
    packet_type = PING
    # Format string for struct: ! = network byte order, I = unsigned int (4 bytes), f = float (4 bytes)
    # Total size for PING payload: 4 (sequence) + 8 (timestamp - double usually in Python) = 12 bytes
    # Let's use 'd' for double for timestamp for better precision and common use
    PAYLOAD_FORMAT = '!Id' # Unsigned int, Double
    PAYLOAD_SIZE = struct.calcsize(PAYLOAD_FORMAT)

    def __init__(self, sequence: int, timestamp: float):
        self.sequence = sequence
        self.timestamp = timestamp

    def to_payload_bytes(self) -> bytes:
        """Packs sequence and timestamp into bytes."""
        return struct.pack(self.PAYLOAD_FORMAT, self.sequence, self.timestamp)

    @classmethod
    def from_payload_bytes(cls, payload_data: bytes) -> 'PingPacket':
        """Unpacks bytes into sequence and timestamp."""
        if len(payload_data) != cls.PAYLOAD_SIZE:
            raise NetError(f"Invalid PING payload size. Expected {cls.PAYLOAD_SIZE}, got {len(payload_data)}.")
        sequence, timestamp = struct.unpack(cls.PAYLOAD_FORMAT, payload_data)
        return cls(sequence=sequence, timestamp=timestamp)

    def __repr__(self) -> str:
        return (f"PingPacket(sequence={self.sequence}, "
                f"timestamp={self.timestamp:.6f}, type={self.packet_type})")

class PongPacket(Packet):
    packet_type = PONG
    # Format string for struct: ! = network byte order, I = unsigned int, d = double (float)
    # Total size for PONG payload: 4 (original_sequence) + 8 (original_timestamp) + 8 (response_timestamp) = 20 bytes
    PAYLOAD_FORMAT = '!Idd' # Unsigned int, Double, Double
    PAYLOAD_SIZE = struct.calcsize(PAYLOAD_FORMAT)

    def __init__(self, original_sequence: int, original_timestamp: float, response_timestamp: float):
        self.original_sequence = original_sequence
        self.original_timestamp = original_timestamp
        self.response_timestamp = response_timestamp

    def to_payload_bytes(self) -> bytes:
        """Packs original_sequence, original_timestamp, and response_timestamp into bytes."""
        return struct.pack(self.PAYLOAD_FORMAT,
                           self.original_sequence,
                           self.original_timestamp,
                           self.response_timestamp)

    @classmethod
    def from_payload_bytes(cls, payload_data: bytes) -> 'PongPacket':
        """Unpacks bytes into original_sequence, original_timestamp, and response_timestamp."""
        if len(payload_data) != cls.PAYLOAD_SIZE:
            raise NetError(f"Invalid PONG payload size. Expected {cls.PAYLOAD_SIZE}, got {len(payload_data)}.")
        original_sequence, original_timestamp, response_timestamp = struct.unpack(cls.PAYLOAD_FORMAT, payload_data)
        return cls(original_sequence=original_sequence,
                   original_timestamp=original_timestamp,
                   response_timestamp=response_timestamp)

    def __repr__(self) -> str:
        return (f"PongPacket(original_sequence={self.original_sequence}, "
                f"original_timestamp={self.original_timestamp:.6f}, "
                f"response_timestamp={self.response_timestamp:.6f}, type={self.packet_type})")

class RawBytesPacket(Packet):
    """A generic packet type for arbitrary raw bytes payloads."""
    # This could be used for FRAME or other simple byte streams
    packet_type = 0 # Placeholder, should be assigned a specific type if used directly

    def __init__(self, raw_data: bytes = b''):
        self.raw_data = raw_data

    def to_payload_bytes(self) -> bytes:
        return self.raw_data

    @classmethod
    def from_payload_bytes(cls, payload_data: bytes) -> 'RawBytesPacket':
        return cls(raw_data=payload_data)

    def __repr__(self) -> str:
        return f"RawBytesPacket(data_len={len(self.raw_data)}, type={self.packet_type})"

# --- Specific Packet Implementation: FramePacket ---
FRAME = 3

class FramePacket(Packet):
    packet_type = FRAME
    # Header format for frame data:
    # ! = network byte order
    # I = unsigned int (frame_id)
    # I = unsigned int (block_id)
    # I = unsigned int (total_blocks_in_frame)
    # I = unsigned int (width)
    # I = unsigned int (height)
    # B = unsigned char (depth, usually 3)
    # Total header size = 4*5 + 1 = 21 bytes
    FRAME_HEADER_FORMAT = '!IIIIIB'
    FRAME_HEADER_SIZE = struct.calcsize(FRAME_HEADER_FORMAT)

    def __init__(self, frame_id: int, block_id: int, total_blocks_in_frame: int,
                 width: int, height: int, depth: int, block_data: bytes):
        super().__init__()
        self.frame_id = frame_id
        self.block_id = block_id
        self.total_blocks_in_frame = total_blocks_in_frame
        self.width = width
        self.height = height
        self.depth = depth
        self.block_data = block_data # Raw bytes of the block slice

    def to_payload_bytes(self) -> bytes:
        """Packs frame metadata and raw block data into bytes."""
        header_bytes = struct.pack(self.FRAME_HEADER_FORMAT,
                                   self.frame_id,
                                   self.block_id,
                                   self.total_blocks_in_frame,
                                   self.width,
                                   self.height,
                                   self.depth)
        return header_bytes + self.block_data

    @classmethod
    def from_payload_bytes(cls, payload_data: bytes) -> 'FramePacket':
        """Unpacks bytes into frame metadata and raw block data."""
        if len(payload_data) < cls.FRAME_HEADER_SIZE:
            raise NetError(f"Incomplete FramePacket header. Expected at least {cls.FRAME_HEADER_SIZE}, got {len(payload_data)}.")

        header_values = struct.unpack_from(cls.FRAME_HEADER_FORMAT, payload_data, 0)
        frame_id, block_id, total_blocks_in_frame, width, height, depth = header_values

        block_data = payload_data[cls.FRAME_HEADER_SIZE:]

        if len(block_data) == 0 and total_blocks_in_frame > 0:
             print(f"Warning: FramePacket block_data is empty for block {block_id} of frame {frame_id}. Is this expected?")

        return cls(frame_id=frame_id, block_id=block_id,
                   total_blocks_in_frame=total_blocks_in_frame,
                   width=width, height=height, depth=depth,
                   block_data=block_data)

    def __repr__(self) -> str:
        return (f"FramePacket(frame_id={self.frame_id}, block_id={self.block_id}/"
                f"{self.total_blocks_in_frame}, size={self.width}x{self.height}x{self.depth}, "
                f"block_data_len={len(self.block_data)} bytes, type={self.packet_type})")


# --- Packet Registry for Clean Decoding ---
_packet_registry: Dict[int, Type[Packet]] = {}

def register_packet_type(packet_class: Type[Packet]):
    """Registers a packet class with its type for decoding."""
    print(f"net.register_packet_type({packet_class})")
    if not issubclass(packet_class, Packet):
        raise TypeError("packet_class must be a subclass of Packet")
    if packet_class.packet_type == 0:
        raise ValueError(f"Packet class {packet_class.__name__} must define a non-zero 'packet_type'.")
    is_overwriting = packet_class.packet_type in _packet_registry
    if is_overwriting:
        print(f"Warning: Overwriting packet type {packet_class.packet_type} ({_packet_registry[packet_class.packet_type].__name__}) with {packet_class.__name__} in global registry.")
    _packet_registry[packet_class.packet_type] = packet_class
    print(f"{_packet_registry=}")
    if not is_overwriting: # Only print for new registrations
        print(f"Registered packet type {packet_class.packet_type}: {packet_class.__name__}")


# Register our current packets
register_packet_type(PingPacket)
register_packet_type(PongPacket)
register_packet_type(FramePacket)

# --- Encoding/Decoding Functions (Now use Packet objects' to/from_payload_bytes) ---

def encode_packet(packet_obj: Packet) -> bytes:
    """
    Encodes a Packet object into bytes.
    The payload is generated by packet_obj.to_payload_bytes().
    """
    if not isinstance(packet_obj, Packet):
        raise TypeError("Input must be a Packet object.")
    if packet_obj.packet_type not in PACKET_TYPE_MAP:
        raise ValueError(f"Packet object has unknown packet type: {packet_obj.packet_type}")

    packet_type_byte = packet_obj.packet_type
    payload_bytes = packet_obj.to_payload_bytes()
    payload_length = len(payload_bytes)

    if payload_length > 65535: # Max 2-byte unsigned integer
        raise NetError("Packet payload too large.")

    # Format: 1 byte for type, 2 bytes for payload length, then payload
    header = struct.pack('!BH', packet_type_byte, payload_length)
    return header + payload_bytes

def decode_packet(data: bytes) -> Packet:
    """
    Decodes bytes into a Packet object based on its type.
    """
    if len(data) < 3: # Minimum 1 byte type + 2 bytes length
        raise NetError("Received data too short to be a valid packet.")

    # Unpack header: 1 byte type, 2 bytes payload length
    packet_type, payload_length = struct.unpack_from('!BH', data, 0)

    if packet_type not in _packet_registry:
        raise NetError(f"Unknown packet type received: {packet_type}. No registered class for it.")

    expected_total_length = 3 + payload_length
    if len(data) < expected_total_length:
        raise NetError(f"Incomplete packet received. Expected {expected_total_length} bytes, got {len(data)}.")

    payload_data = data[3:expected_total_length]

    # Use the registry to get the correct Packet class and create an instance
    packet_class = _packet_registry[packet_type]
    return packet_class.from_payload_bytes(payload_data)

class UDPSender:
    def __init__(self, target_host: str, target_port: int, bind_port: int = 0):
        self.target_host = target_host
        self.target_port = target_port
        self.bind_port = bind_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.1) # Timeout for listen_for_response
        if self.bind_port != 0:
            self.sock.bind(('', self.bind_port))
        print(f"UDP Sender initialized. Sending to {target_host}:{target_port}")
        if self.bind_port != 0:
            print(f"Bound to local port: {self.sock.getsockname()[1]}")

        self.current_frame_id = 0
        self.previous_frame = None

    def send_packet(self, packet_obj: Packet):
        # Use the global encode_packet function
        encoded_packet = encode_packet(packet_obj)
        try:
            self.sock.sendto(encoded_packet, (self.target_host, self.target_port))
        except OSError as e:
            print(f"Error sending packet: {e}")

    def send_ping(self, sequence_number: int):
        ping_packet = PingPacket(sequence=sequence_number, timestamp=time.time())
        self.send_packet(ping_packet)

    def send_frame(self, frame: np.ndarray, max_block_side_len: int = 64):
        """
        Splits a video frame into smaller blocks, creates FramePackets for changed blocks,
        and sends them via UDP. Implements basic differencing to reduce bandwidth.

        Args:
            frame (np.ndarray): The NumPy array representing the video frame (H, W, C).
            max_block_side_len (int): The maximum side length (in pixels) for each
                                      square block. Actual block size might be smaller
                                      at the edges of the frame.
        """
        if frame.dtype != np.uint8:
            print("Warning: Frame is not uint8. Converting.")
            frame = frame.astype(np.uint8)

        height, width, depth = frame.shape
        if depth != 3:
            print(f"Warning: Frame depth is {depth}, expected 3 (RGB).")

        if max_block_side_len <= 0:
            max_block_side_len = 1
            print("Warning: max_block_side_len must be positive. Using 1.")

        block_side_len = max_block_side_len

        # Calculate number of blocks needed in X and Y directions
        num_blocks_x = math.ceil(width / block_side_len)
        num_blocks_y = math.ceil(height / block_side_len)
        total_blocks = num_blocks_x * num_blocks_y

        self.current_frame_id += 1 # Increment frame ID for each new frame sent

        blocks_sent_count = 0
        for y_idx in range(num_blocks_y):
            for x_idx in range(num_blocks_x):
                block_id = y_idx * num_blocks_x + x_idx # Unique ID for each block within the frame

                # Determine the coordinates for the current block
                x_start = x_idx * block_side_len
                y_start = y_idx * block_side_len
                x_end = min(x_start + block_side_len, width)  # Ensure x_end doesn't exceed frame width
                y_end = min(y_start + block_side_len, height) # Ensure y_end doesn't exceed frame height

                current_block = frame[y_start:y_end, x_start:x_end, :]

                block_changed = True
                # Basic differencing: Compare with the corresponding block from the previous frame
                if self.previous_frame is not None and self.previous_frame.shape == frame.shape:
                    previous_block = self.previous_frame[y_start:y_end, x_start:x_end, :]
                    if np.array_equal(current_block, previous_block): # Check if blocks are identical
                        block_changed = False

                if block_changed:
                    block_data_bytes = current_block.tobytes()

                    frame_packet = FramePacket(
                        frame_id=self.current_frame_id,
                        block_id=block_id,
                        total_blocks_in_frame=total_blocks,
                        width=width,
                        height=height,
                        depth=depth,
                        block_data=block_data_bytes
                    )
                    self.send_packet(frame_packet) # Send the created FramePacket
                    blocks_sent_count += 1

        # Store a copy of the current frame for differencing in the next iteration
        self.previous_frame = frame.copy()

    def listen_for_response(self, timeout: float = 0.1) -> Optional[Packet]:
        try:
            self.sock.settimeout(timeout)
            data, addr = self.sock.recvfrom(65535)
            decoded_packet = decode_packet(data) # Use global decode_packet
            return decoded_packet
        except socket.timeout:
            return None
        except NetError as e:
            print(f"Error decoding received packet by sender: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred while sender listening: {e}")
            return None

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None

# --- UDPReceiver Class (Uses Packet objects and a Handler Dispatcher) ---
class UDPReceiver:
    def __init__(self, listen_host: str, listen_port: int):
        self.listen_host = listen_host
        self.listen_port = listen_port

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.listen_host, self.listen_port))
        self.sock.settimeout(0.01)

        print(f"UDP Receiver listening on {self.listen_host}:{self.listen_port}")
        self._packet_handlers: Dict[int, Callable[[Packet, tuple], None]] = {}

        # Register default handlers (can be overridden or extended)
        self.register_packet_handler(PING, self._handle_ping_packet)
        self.register_packet_handler(PONG, self._handle_pong_packet) # Receiver might get PONGs in some scenarios too
        self.register_packet_handler(FRAME, self._handle_frame_packet)

        self.frame_buffers: Dict[int, Dict[str, Any]] = {}
        self.frame_timeout_sec: float = 2.0 # How long to wait for all blocks of a frame
        self.nominal_block_side_len: int = 64 # Must match sender's block size
        self.last_displayed_frame_id: int = -1 # Track the last displayed frame ID

    def register_packet_handler(self, packet_type: int, handler_func: Callable[[Packet, tuple], None]):
        """Registers a function to handle a specific packet type."""
        if packet_type not in PACKET_TYPE_MAP:
            print(f"Warning: Registering handler for unknown packet type: {packet_type}")
        self._packet_handlers[packet_type] = handler_func
        print(f"Registered handler for packet type {PACKET_TYPE_MAP.get(packet_type, str(packet_type))}")

    def _handle_frame_packet(self, frame_packet: FramePacket, sender_address: tuple):
        """Default handler for PONG packets (receiver might get them)."""
        print(f"Handling FRAME {repr(self)} rom {sender_address}")
        if len(current_frame_info['received_blocks']) == current_frame_info['total_blocks']:
            # All blocks for this frame have arrived!
            # Now, check if this is a newer frame than what was last displayed
            if frame_id > self.last_displayed_frame_id:
                self._display_frame(current_frame_info['ndarray'], frame_id)
                self.last_displayed_frame_id = frame_id # Update the last displayed ID
            # Delete the frame buffer entry as it's complete and handled
            del self.frame_buffers[frame_id]
    def _display_frame(self, frame_ndarray: np.ndarray, frame_id: int):
        # import cv2 # You might want this here if not global, or at the top of the file
        cv2.imshow(f'Received Frame (ID: {frame_id})', frame_ndarray)

    def _cleanup_frame_buffers(self):
        current_time = time.time()
        frames_to_remove = []
        for frame_id, info in self.frame_buffers.items():
            if current_time - info['last_received_time'] > self.frame_timeout_sec:
                frames_to_remove.append(frame_id)

        for frame_id in frames_to_remove:
            print(f"Timeout: Purging incomplete frame {frame_id}.")
            del self.frame_buffers[frame_id]

    def start_listening(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(65535)  # Buffer size
                print(f"Received raw data from {addr}")
                try:
                    decoded_packet = decode_packet(data)
                    print(f"Decoded {decoded_packet.__class__.__name__} from {addr}: {decoded_packet}")

                    handler = self._packet_handlers.get(decoded_packet.packet_type)
                    if callable(handler):
                        handler(decoded_packet, addr)
                    else:
                        print(f"No handler registered for packet type: {decoded_packet.packet_type}")
                except NetError as e:
                    print(f"Error decoding received packet from {addr}: {e}")
                except Exception as e:
                    print(f"An unexpected error occurred during packet processing from {addr}: {e}")

            except socket.timeout as e:
                # This block is executed if no data is received within the timeout period
                # print("Socket timeout: No data received.") # Optional debug print
                self._cleanup_frame_buffers() # Clean up old incomplete frames
                cv2.waitKey(1)
                continue
            except KeyboardInterrupt:
                print("\nReceiver stopped by user.")
                break
            except Exception as e:
                print(f"An error occurred while listening: {e}")
                break

    def _handle_ping_packet(self, ping_packet: PingPacket, sender_address: tuple):
        """Default handler for PING packets."""
        print(f"Handling PING (seq={ping_packet.sequence}) from {sender_address}")
        self._send_pong(sender_address, ping_packet)

    def _handle_pong_packet(self, pong_packet: PongPacket, sender_address: tuple):
        """Default handler for PONG packets (receiver might get them)."""
        print(f"Handling PONG (orig_seq={pong_packet.original_sequence}) from {sender_address}")
        # In a real app, receiver might just log this or do nothing for a PONG it didn't expect

    def _send_pong(self, target_address: tuple, ping_packet: PingPacket):
        pong_packet = PongPacket(
            original_sequence=ping_packet.sequence,
            original_timestamp=ping_packet.timestamp,
            response_timestamp=time.time()
        )
        encoded_pong = encode_packet(pong_packet)
        self.sock.sendto(encoded_pong, target_address)
        print(f"Sent PONG to {target_address} for PING (seq={ping_packet.sequence})")

    def close(self):
        self.sock.close()
        print("UDP Receiver closed.")
