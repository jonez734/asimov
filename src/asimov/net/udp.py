# asimov/net/udp.py
# UDP sender/receiver classes with frame transmission support

import socket
import struct
import time
import zlib
import math
from typing import Optional, Callable, Any
from collections import defaultdict

import numpy as np

from .packet import (
    encode_packet, decode_packet, 
    PACKET_TYPE_PING, PACKET_TYPE_PONG, PACKET_TYPE_EOS, PACKET_TYPE_FRAME,
    FramePacket, encode_frame_packet, decode_frame_packet,
    PING, PONG, EOS,
    FRAME_PACKET_HEADER_SIZE
)
from .conf import BUFFER_SIZE


UDP_MAX_PAYLOAD = 65507 - 28 - FRAME_PACKET_HEADER_SIZE


def _calc_optimal_blocks_per_packet(block_w: int, block_h: int, compress: bool) -> int:
    """Calculate max blocks that fit in UDP packet."""
    block_size = block_w * block_h * 3
    if compress:
        block_size = max(block_size // 10, 100)
    return max(1, UDP_MAX_PAYLOAD // block_size)


class UDPSender:
    def __init__(self, host: str, port: int, bind_port: int = 0, blocking: bool = False):
        self.host = host
        self.port = port
        self.addr = (host, port)
        self.blocking = blocking
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        if bind_port > 0:
            self.sock.bind(('0.0.0.0', bind_port))
        else:
            self.sock.bind(('0.0.0.0', 0))
        
        if not blocking:
            self.sock.setblocking(False)
        
        self.prev_frame = None

    def send_frame(
        self,
        frame: np.ndarray,
        frame_id: int,
        prev_frame: np.ndarray = None,
        cols: int = 0,
        rows: int = 0,
        compress: bool = False,
        full_frame: bool = False,
        auto_batch: bool = True
    ):
        """
        Send frame - default: delta frames with auto-batching.
        
        Args:
            frame: The frame to send
            frame_id: Unique frame identifier
            prev_frame: Previous frame for delta. If None, uses self.prev_frame.
            cols, rows: Grid dimensions. Auto-calculated if not provided.
            compress: Enable zlib compression
            full_frame: If True, send all blocks (not just changes)
            auto_batch: If True, automatically batch blocks to fill UDP packets
        """
        height, width = frame.shape[:2]
        
        if prev_frame is None:
            prev_frame = self.prev_frame
        
        is_delta = not full_frame and prev_frame is not None
        
        if cols <= 0 or rows <= 0:
            max_block_size = 64
            block_size = min(max_block_size, math.gcd(width, height))
            if block_size < 8:
                block_size = 8
            cols = (width + block_size - 1) // block_size
            rows = (height + block_size - 1) // block_size
        
        block_w = width // cols
        block_h = height // rows
        total_blocks = cols * rows
        
        blocks_per_packet = 1
        if auto_batch:
            blocks_per_packet = _calc_optimal_blocks_per_packet(block_w, block_h, compress)
        
        if is_delta:
            from asimov.util import get_changed_blocks
            changed = get_changed_blocks(frame, prev_frame, frame_id, compress)
            block_ids = [b.id for b in changed]
            block_datas = {b.id: b.data for b in changed}
        else:
            block_ids = list(range(total_blocks))
            block_datas = {}
        
        for i in range(0, len(block_ids), blocks_per_packet):
            batch_ids = block_ids[i:i + blocks_per_packet]
            blocks = []
            
            for block_id in batch_ids:
                if block_id in block_datas:
                    data = block_datas[block_id]
                else:
                    row = block_id // cols
                    col = block_id % cols
                    x0 = col * block_w
                    y0 = row * block_h
                    x1 = min(x0 + block_w, width)
                    y1 = min(y0 + block_h, height)
                    
                    chunk = frame[y0:y1, x0:x1]
                    data = chunk.tobytes()
                
                if compress:
                    data = zlib.compress(data)
                
                blocks.append(data)
            
            packet = FramePacket(
                frame_id=frame_id,
                block_id=batch_ids[0] if batch_ids else 0,
                cols=cols,
                rows=rows,
                block_w=block_w,
                block_h=block_h,
                total_blocks=total_blocks,
                is_delta=is_delta,
                compressed=compress,
                blocks=blocks,
                blocks_in_packet=len(blocks),
                timestamp=time.time()
            )
            
            encoded = encode_frame_packet(packet)
            self.sock.sendto(encoded, self.addr)
        
        self.prev_frame = frame.copy()

    def send_ping(self):
        """Send a PING packet."""
        data = encode_packet(PACKET_TYPE_PING)
        self.sock.sendto(data, self.addr)

    def send_pong(self, timestamp: float = 0.0):
        """Send a PONG packet."""
        ts = timestamp if timestamp != 0.0 else time.time()
        data = encode_packet(PACKET_TYPE_PONG, timestamp=ts)
        self.sock.sendto(data, self.addr)

    def send_eos(self):
        """Send an End-of-Stream packet."""
        data = encode_packet(PACKET_TYPE_EOS)
        self.sock.sendto(data, self.addr)

    def receive(self, timeout: float = 0.5) -> Optional[dict]:
        """Receive a packet (non-blocking)."""
        self.sock.setblocking(False)
        try:
            self.sock.settimeout(timeout)
            data, addr = self.sock.recvfrom(BUFFER_SIZE)
            if data:
                return decode_packet(data)
        except socket.timeout:
            pass
        except BlockingIOError:
            pass
        return None

    def close(self):
        self.sock.close()


class UDPReceiver:
    def __init__(
        self, 
        host: str, 
        port: int, 
        frame_received_callback: Optional[Callable] = None,
        idle_callback: Optional[Callable] = None,
        local_port: int = 0,
        blocking: bool = True,
        timeout: float = 0.5
    ):
        self.host = host
        self.port = port
        self.addr = (host, port)
        self.blocking = blocking
        self.timeout = timeout
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 10 * 1024 * 1024)  # 10MB
        self.sock.bind(('0.0.0.0', port))
        
        if not blocking:
            self.sock.setblocking(False)
        
        self.sock.settimeout(timeout)
        
        self.frame_received_callback = frame_received_callback
        self.idle_callback = idle_callback
        
        self.frames = defaultdict(dict)
        self.frame_meta = {}
        self.prev_frame = None
        self.prev_frame_meta = {}
        self.last_displayed_frame_id = -1
        self.running = False

    def start_listening(self):
        """Start listening for frames in a loop."""
        self.running = True
        try:
            while self.running:
                self.receive()
                
                if self.idle_callback:
                    if not self.idle_callback():
                        break
        finally:
            self.close()

    def receive(self) -> Any:
        """Receive and reassemble frames."""
        try:
            self.sock.settimeout(self.timeout)
            data, addr = self.sock.recvfrom(BUFFER_SIZE)
        except socket.timeout:
            return None
        except BlockingIOError:
            return None

        if not data:
            return None

        packet_type_raw = struct.unpack("!B", data[:1])[0]

        if packet_type_raw == PACKET_TYPE_PING:
            self.send_pong()
            return PING
        elif packet_type_raw == PACKET_TYPE_PONG:
            return PONG
        elif packet_type_raw == PACKET_TYPE_EOS:
            return EOS
        elif packet_type_raw == PACKET_TYPE_FRAME:
            return self._handle_frame_packet(data)
        
        return None

    def _handle_frame_packet(self, data: bytes) -> Optional[np.ndarray]:
        """Handle an incoming frame packet and reassemble if complete."""
        try:
            packet = decode_frame_packet(data)
        except Exception as e:
            print(f"Failed to decode frame packet: {e}")
            return None

        frame_id = packet.frame_id
        cols = packet.cols
        rows = packet.rows
        block_w = packet.block_w
        block_h = packet.block_h
        total_blocks = packet.total_blocks
        is_delta = packet.is_delta
        compressed = packet.compressed
        
        width = cols * block_w
        height = rows * block_h
        
        self.frame_meta[frame_id] = {
            'cols': cols,
            'rows': rows,
            'block_w': block_w,
            'block_h': block_h,
            'width': width,
            'height': height,
            'total_blocks': total_blocks,
            'is_delta': is_delta,
            'compressed': compressed
        }
        
        for i, block_data in enumerate(packet.blocks):
            block_id = packet.block_id + i
            
            if compressed:
                try:
                    block_data = zlib.decompress(block_data)
                except zlib.error as e:
                    print(f"Failed to decompress block {block_id}: {e}")
                    continue
            
            self.frames[frame_id][block_id] = block_data

        received_count = len(self.frames[frame_id])
        
        if received_count >= total_blocks:
            return self._reassemble_frame(frame_id)

        return None

    def _reassemble_frame(self, frame_id: int) -> Optional[np.ndarray]:
        """Reassemble a complete frame from chunks."""
        if frame_id not in self.frames:
            return None

        meta = self.frame_meta[frame_id]
        cols = meta['cols']
        block_w = meta['block_w']
        block_h = meta['block_h']
        width = meta['width']
        height = meta['height']
        is_delta = meta['is_delta']
        
        blocks = self.frames[frame_id]
        
        if is_delta and self.prev_frame is not None and self.prev_frame.shape == (height, width, 3):
            full_frame = self.prev_frame.copy()
            apply_to_prev = True
        else:
            full_frame = np.zeros((height, width, 3), dtype=np.uint8)
            apply_to_prev = False
        
        for block_id, block_data in blocks.items():
            row = block_id // cols
            col = block_id % cols
            x = col * block_w
            y = row * block_h
            
            try:
                block_img = np.frombuffer(block_data, dtype=np.uint8).reshape((block_h, block_w, 3))
            except ValueError:
                continue
            
            h, w = block_img.shape[:2]
            full_frame[y:y+h, x:x+w] = block_img

        del self.frames[frame_id]
        self.frame_meta.pop(frame_id, None)
        
        if apply_to_prev:
            for block_id, block_data in blocks.items():
                row = block_id // cols
                col = block_id % cols
                x = col * block_w
                y = row * block_h
                
                try:
                    block_img = np.frombuffer(block_data, dtype=np.uint8).reshape((block_h, block_w, 3))
                except ValueError:
                    continue
                
                h, w = block_img.shape[:2]
                self.prev_frame[y:y+h, x:x+w] = block_img
        else:
            self.prev_frame = full_frame.copy()
        
        self.prev_frame_meta = meta

        if self.frame_received_callback:
            self.frame_received_callback(full_frame, frame_id)

        return full_frame.copy()

    def send_pong(self, timestamp: float = 0.0):
        """Send a PONG response."""
        ts = timestamp if timestamp != 0.0 else time.time()
        data = encode_packet(PACKET_TYPE_PONG, timestamp=ts)
        self.sock.sendto(data, self.addr)

    def close(self):
        self.running = False
        self.sock.close()
