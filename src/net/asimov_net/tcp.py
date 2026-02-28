# asimov/net/tcp.py
# TCP sender/receiver classes with frame transmission support

import socket
import struct
import time
import zlib
import math
from typing import Optional

import numpy as np

from .packet import Packet

from .frame import (
    FramePacket,
    encode_frame_packet,
    FRAME_PACKET_HEADER_SIZE,
)


def _calc_optimal_blocks_per_packet(block_w: int, block_h: int, compress: bool) -> int:
    """Calculate max blocks that fit in TCP packet."""
    TCP_MAX_PAYLOAD = 65507 - FRAME_PACKET_HEADER_SIZE
    block_size = block_w * block_h * 3
    if compress:
        block_size = max(block_size // 10, 100)
    return max(1, TCP_MAX_PAYLOAD // block_size)


class TCPSender:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None

    def connect(self):
        if self.sock is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))

    def send(self, packet: Packet):
        if self.sock is None:
            raise RuntimeError("TCPSender.send(): not connected")
        self.sock.sendall(packet.encode())

    def send_frame(
        self,
        frame: np.ndarray,
        frame_id: int,
        prev_frame: np.ndarray = None,
        cols: int = 0,
        rows: int = 0,
        compress: bool = False,
        full_frame: bool = False,
        auto_batch: bool = True,
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
            auto_batch: If True, automatically batch blocks to fill TCP packets
        """
        if self.sock is None:
            self.connect()

        height, width = frame.shape[:2]

        if prev_frame is None:
            prev_frame = getattr(self, "prev_frame", None)

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
            blocks_per_packet = _calc_optimal_blocks_per_packet(
                block_w, block_h, compress
            )

        if is_delta:
            from asimov.util import get_changed_blocks

            changed = get_changed_blocks(frame, prev_frame, frame_id, compress)
            block_ids = [b.id for b in changed]
            block_datas = {b.id: b.data for b in changed}
        else:
            block_ids = list(range(total_blocks))
            block_datas = {}

        for i in range(0, len(block_ids), blocks_per_packet):
            batch_ids = block_ids[i : i + blocks_per_packet]
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
                width=width,
                height=height,
                total_blocks=total_blocks,
                is_delta=is_delta,
                compressed=compress,
                blocks=blocks,
                blocks_in_packet=len(blocks),
                timestamp=time.time(),
            )

            encoded = encode_frame_packet(packet)
            self.sock.sendall(encoded)

        self.prev_frame = frame.copy()

    def recv(self) -> Optional[Packet]:
        if self.sock is None:
            raise RuntimeError("TCPSender.recv(): not connected")
        return Packet.recv(self.sock)

    def close(self):
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.sock.close()
            self.sock = None


class TCPReceiver:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5000,
        blocking: bool = False,
        timeout: float = 1.0,
    ):
        self.host = host
        self.port = port
        self.blocking = blocking
        self.timeout = timeout

        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((self.host, self.port))
        self.server_sock.listen(1)
        self.server_sock.settimeout(timeout if not blocking else None)

        self.client_sock: Optional[socket.socket] = None
        self._accept_connection()

    def _accept_connection(self):
        """Accept incoming TCP connection."""
        if self.client_sock is None:
            self.client_sock, addr = self.server_sock.accept()
            self.client_sock.settimeout(self.timeout if not self.blocking else None)

    def receive(self) -> Optional[FramePacket]:
        """Receive a frame packet."""
        if self.client_sock is None:
            try:
                self._accept_connection()
            except socket.timeout:
                return None

        try:
            header = self._recv_exact(FRAME_PACKET_HEADER_SIZE)
            if header is None:
                return None

            (
                frame_id,
                block_id,
                cols,
                rows,
                block_w,
                block_h,
                width,
                height,
                total_blocks,
                flags,
                blocks_in_packet,
                timestamp,
            ) = struct.unpack("!I I H H H H H H I ? I d", header)

            is_delta = bool(flags & 0x01)
            compressed = bool(flags & 0x02)

            blocks = []
            for _ in range(blocks_in_packet):
                block_len_bytes = self._recv_exact(4)
                if block_len_bytes is None:
                    return None
                block_len = struct.unpack("!I", block_len_bytes)[0]

                block_data = self._recv_exact(block_len)
                if block_data is None:
                    return None

                if compressed:
                    block_data = zlib.decompress(block_data)

                blocks.append(block_data)

            return FramePacket(
                frame_id=frame_id,
                block_id=block_id,
                cols=cols,
                rows=rows,
                block_w=block_w,
                block_h=block_h,
                width=width,
                height=height,
                total_blocks=total_blocks,
                is_delta=is_delta,
                compressed=compressed,
                blocks=blocks,
                blocks_in_packet=blocks_in_packet,
                timestamp=timestamp,
            )

        except socket.timeout:
            return None
        except Exception:
            self.client_sock = None
            return None

    def _recv_exact(self, n: int) -> Optional[bytes]:
        """Receive exactly n bytes from socket."""
        if self.client_sock is None:
            return None

        data = b""
        while len(data) < n:
            try:
                chunk = self.client_sock.recv(n - len(data))
                if not chunk:
                    return None
                data += chunk
            except socket.timeout:
                return None
        return data

    def close(self):
        if self.client_sock:
            try:
                self.client_sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.client_sock.close()
            self.client_sock = None

        if self.server_sock:
            self.server_sock.close()
            self.server_sock = None
