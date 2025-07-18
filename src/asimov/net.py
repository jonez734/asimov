# net.py
import struct
import socket
import time
from typing import Dict, Any, Type, Callable, Optional
from abc import ABC, abstractmethod

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

# --- Packet Registry for Clean Decoding ---
_packet_registry: Dict[int, Type[Packet]] = {}

def register_packet_type(packet_class: Type[Packet]):
    """Registers a packet class with its type for decoding."""
    if not issubclass(packet_class, Packet):
        raise TypeError("packet_class must be a subclass of Packet")
    if packet_class.packet_type == 0:
        raise ValueError(f"Packet class {packet_class.__name__} must define a non-zero 'packet_type'.")
    if packet_class.packet_type in _packet_registry:
        print(f"Warning: Overwriting packet type {packet_class.packet_type} in registry.")
    _packet_registry[packet_class.packet_type] = packet_class

# Register our current packets
register_packet_type(PingPacket)
register_packet_type(PongPacket)


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


# --- UDPSender Class (Minimal changes, uses Packet objects) ---
class UDPSender:
    def __init__(self, target_host: str, target_port: int, bind_port: int = 0):
        self.target_host = target_host
        self.target_port = target_port
        self.bind_port = bind_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if self.bind_port != 0:
            self.sock.bind(('', self.bind_port))
        print(f"UDP Sender initialized. Sending to {target_host}:{target_port}")
        if self.bind_port != 0:
            print(f"Bound to local port: {self.sock.getsockname()[1]}")

    def send_packet(self, packet_obj: Packet):
        """Generic method to send any Packet object."""
        encoded_packet = encode_packet(packet_obj)
        self.sock.sendto(encoded_packet, (self.target_host, self.target_port))
        print(f"Sent {packet_obj.__class__.__name__} to {self.target_host}:{self.target_port}: {packet_obj}")

    def send_ping(self, sequence_number: int):
        """Helper for sending PINGs using the new PingPacket."""
        ping_packet = PingPacket(sequence=sequence_number, timestamp=time.time())
        self.send_packet(ping_packet)

    def listen_for_response(self, timeout: float = 5.0) -> Optional[Packet]:
        self.sock.settimeout(timeout)
        try:
            data, addr = self.sock.recvfrom(4096)  # Buffer size
            decoded_packet = decode_packet(data)
            print(f"Received {decoded_packet.__class__.__name__} from {addr}: {decoded_packet}")
            return decoded_packet
        except socket.timeout:
            print(f"No response received within {timeout} seconds.")
            return None
        except NetError as e:
            print(f"Error decoding received packet: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred while listening: {e}")
            return None

    def close(self):
        self.sock.close()
        print("UDP Sender closed.")

# --- UDPReceiver Class (Uses Packet objects and a Handler Dispatcher) ---
class UDPReceiver:
    def __init__(self, listen_host: str, listen_port: int):
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.listen_host, self.listen_port))
        print(f"UDP Receiver listening on {self.listen_host}:{self.listen_port}")
        self._packet_handlers: Dict[int, Callable[[Packet, tuple], None]] = {}

        # Register default handlers (can be overridden or extended)
        self.register_packet_handler(PING, self._handle_ping_packet)
        self.register_packet_handler(PONG, self._handle_pong_packet) # Receiver might get PONGs in some scenarios too

    def register_packet_handler(self, packet_type: int, handler_func: Callable[[Packet, tuple], None]):
        """Registers a function to handle a specific packet type."""
        if packet_type not in PACKET_TYPE_MAP:
            print(f"Warning: Registering handler for unknown packet type: {packet_type}")
        self._packet_handlers[packet_type] = handler_func
        print(f"Registered handler for packet type {PACKET_TYPE_MAP.get(packet_type, str(packet_type))}")

    def start_listening(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(4096)  # Buffer size
                print(f"Received raw data from {addr}")
                try:
                    decoded_packet = decode_packet(data)
                    print(f"Decoded {decoded_packet.__class__.__name__} from {addr}: {decoded_packet}")

                    handler = self._packet_handlers.get(decoded_packet.packet_type)
                    if handler:
                        handler(decoded_packet, addr)
                    else:
                        print(f"No handler registered for packet type: {decoded_packet.packet_type}")

                except NetError as e:
                    print(f"Error decoding received packet from {addr}: {e}")
                except Exception as e:
                    print(f"An unexpected error occurred during packet processing from {addr}: {e}")

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
