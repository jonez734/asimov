# asimov/network.py

import socket
import struct
import numpy as np
import time
from typing import Union, Dict, Any

import conf # Import the configuration

class UDPReceiver:
    def __init__(self, host: str, port: int, timeout: float = 0.5):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        self.sock.settimeout(self.timeout)
        
        # Buffer for reassembling frames: {frame_id: {'chunks': {chunk_idx: data}, 'received_count': int, 'total_chunks': int, 'last_received_time': float}}
        self.frame_buffers: Dict[int, Dict[str, Any]] = {}
        
        self.expected_full_frame_bytes = np.prod(conf.STATIC_FRAME_SHAPE) * conf.STATIC_FRAME_DTYPE.itemsize
        
        print(f"UDPReceiver initialized. Listening on {self.host}:{self.port}")

    def receive_next_complete_frame_or_signal(self) -> Union[np.ndarray, type(conf.EOS_SIGNAL), None]:
        """
        Attempts to receive UDP packets and reassemble one complete frame.
        Also detects EOS signals.
        
        Returns:
            - A numpy.ndarray if a full frame is successfully reassembled.
            - conf.EOS_SIGNAL if an EOS packet is received.
            - None if a timeout occurs, an incomplete frame is received after a timeout,
              or an unknown/malformed packet is encountered.
            - Raises socket.error or other exceptions for critical issues.
        """
        while True: # Loop to process multiple incoming packets until a full frame or signal
            try:
                packet, addr = self.sock.recvfrom(conf.UDP_MAX_PACKET_SIZE)
                
                if len(packet) < conf.UDP_HEADER_SIZE:
                    print(f"UDPReceiver: Received malformed packet (too small for header): {len(packet)} bytes from {addr}. Discarding.")
                    continue

                header_data = packet[:conf.UDP_HEADER_SIZE]
                payload = packet[conf.UDP_HEADER_SIZE:]

                packet_type, frame_id, chunk_index, total_chunks = \
                    struct.unpack(conf.UDP_HEADER_FORMAT, header_data)

                # --- Handle Packet Type ---
                if packet_type == conf.PACKET_TYPE_EOS:
                    return conf.EOS_SIGNAL # Return EOS signal immediately
                
                elif packet_type == conf.PACKET_TYPE_FRAME:
                    if frame_id not in self.frame_buffers:
                        # Initialize buffer for new frame
                        self.frame_buffers[frame_id] = {
                            'chunks': {},
                            'received_count': 0,
                            'total_chunks': total_chunks,
                            'last_received_time': time.monotonic()
                        }
                    
                    # Store chunk
                    if chunk_index not in self.frame_buffers[frame_id]['chunks']:
                        self.frame_buffers[frame_id]['chunks'][chunk_index] = payload
                        self.frame_buffers[frame_id]['received_count'] += 1
                        self.frame_buffers[frame_id]['last_received_time'] = time.monotonic()
                    # else: print(f"UDPReceiver: Duplicate chunk {chunk_index} for frame {frame_id}. (Ignored)")

                    # Check if all chunks for the current frame are received
                    if self.frame_buffers[frame_id]['received_count'] == total_chunks:
                        # Reconstruct the full frame bytes by sorting and concatenating chunks
                        full_frame_data = b''
                        for i in range(total_chunks):
                            chunk = self.frame_buffers[frame_id]['chunks'].get(i)
                            
                            if chunk is None:
                                print(f"UDPReceiver: Missing chunk {i} for frame {frame_id}. Discarding frame and waiting for next.")
                                del self.frame_buffers[frame_id] # Clean up incomplete frame
                                return None # Indicate incomplete frame/wait for next
                            full_frame_data += chunk
                        
                        # If we made it here, all chunks were collected
                        if len(full_frame_data) != self.expected_full_frame_bytes:
                            print(f"UDPReceiver: Reconstructed frame {frame_id} has incorrect size ({len(full_frame_data)} bytes). Expected {self.expected_full_frame_bytes}. Discarding.")
                            del self.frame_buffers[frame_id]
                            return None # Indicate corrupted frame
                        
                        # Clean up buffer for the successfully reassembled frame
                        del self.frame_buffers[frame_id]
                        
                        # Convert bytes back to numpy array
                        try:
                            reconstructed_frame = np.frombuffer(full_frame_data, dtype=conf.STATIC_FRAME_DTYPE).reshape(conf.STATIC_FRAME_SHAPE)
                            return reconstructed_frame # Return the complete frame
                        except ValueError as e:
                            print(f"UDPReceiver: Error reconstructing numpy array for frame {frame_id}: {e}. Discarding.")
                            return None # Indicate reconstruction error
                else:
                    # If not all chunks are received for the current frame, keep looping
                    # and wait for more packets to arrive for this or subsequent frames.
                    pass # Just continue the while loop to receive more packets
            else:
                print(f"UDPReceiver: Received unknown packet type: {packet_type}. Discarding.")
                return None # Indicate unknown packet type

            except socket.timeout:
                # Cleanup logic for old, incomplete frames
                current_time = time.monotonic()
                frames_to_remove = []
                for fid, buffer_data in self.frame_buffers.items():
                    if current_time - buffer_data['last_received_time'] > 1.0: # 1 second timeout for incomplete frames
                        print(f"UDPReceiver: Timeout on frame {fid} ({buffer_data['received_count']}/{buffer_data['total_chunks']} chunks). Discarding.")
                        frames_to_remove.append(fid)
                for fid in frames_to_remove:
                    del self.frame_buffers[fid]
                
                return None # Indicate timeout, no complete frame received yet
            
            except socket.error as e:
                raise # Re-raise for main loop to handle critical socket errors
            except Exception as e:
                print(f"UDPReceiver: Unexpected error during frame reception/reassembly: {e}")
                import traceback
                traceback.print_exc()
                raise # Re-raise unexpected errors

    def close(self):
        """Closes the UDP socket and cleans up any remaining buffers."""
        if self.sock:
            self.sock.close()
            print("UDPReceiver: Socket closed.")
        self.sock = None
        self.frame_buffers.clear()
        print("UDPReceiver: Frame buffers cleared.")

# my_project/network/udp_sender.py

import conf # Import the configuration

class UDPSender:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_address = (self.host, self.port)
        print(f"UDPSender initialized. Target: {self.host}:{self.port}")

    def send_frame(self, frame_numpy_array: np.ndarray, frame_id: int):
        """
        Sends a single NumPy array frame as a series of UDP chunks.
        Assumes frame_numpy_array matches conf.STATIC_FRAME_SHAPE and conf.STATIC_FRAME_DTYPE.
        """
        if frame_numpy_array.shape != conf.STATIC_FRAME_SHAPE or frame_numpy_array.dtype != conf.STATIC_FRAME_DTYPE:
            raise ValueError(f"Frame shape {frame_numpy_array.shape} or dtype {frame_numpy_array.dtype} does not match static configuration {conf.STATIC_FRAME_SHAPE}, {conf.STATIC_FRAME_DTYPE}.")

        frame_data_bytes = frame_numpy_array.tobytes()
        total_bytes = len(frame_data_bytes)
        total_chunks = math.ceil(total_bytes / conf.UDP_DATA_CHUNK_SIZE)

        for chunk_index in range(total_chunks):
            start_idx = chunk_index * conf.UDP_DATA_CHUNK_SIZE
            end_idx = min(total_bytes, start_idx + conf.UDP_DATA_CHUNK_SIZE)
            current_chunk_payload = frame_data_bytes[start_idx:end_idx]

            # Pack header: packet_type, frame_id, chunk_index, total_chunks
            header = struct.pack(conf.UDP_HEADER_FORMAT,
                                 conf.PACKET_TYPE_FRAME,
                                 frame_id, chunk_index, total_chunks)

            packet = header + current_chunk_payload
            
            try:
                self.sock.sendto(packet, self.server_address)
                # print(f"  Sent frame {frame_id}, chunk {chunk_index+1}/{total_chunks} ({len(packet)} bytes).")
            except socket.error as e:
                # Raise the exception so the caller (capture process) can handle it
                raise ConnectionError(f"Failed to send UDP packet for frame {frame_id}, chunk {chunk_index}: {e}") from e
            
            # Small delay between chunks to avoid overwhelming the network or receiver
            time.sleep(0.00005) # Adjusted slightly for potentially smoother flow

    def send_eos(self, frame_id_for_eos: int = conf.UDP_SHUTDOWN_FRAME_ID):
        """
        Sends an End-of-Stream (EOS) signal over UDP.
        """
        # For EOS, chunk_index and total_chunks are typically 0 or ignored.
        # We use the special UDP_SHUTDOWN_FRAME_ID.
        header = struct.pack(conf.UDP_HEADER_FORMAT,
                             conf.PACKET_TYPE_EOS,
                             frame_id_for_eos, 0, 0)
        try:
            self.sock.sendto(header, self.server_address)
            print(f"UDPSender: Sent EOS signal with frame_id {frame_id_for_eos}.")
        except socket.error as e:
            raise ConnectionError(f"Failed to send UDP EOS signal: {e}") from e

    def close(self):
        """Closes the UDP socket."""
        if self.sock:
            self.sock.close()
            print("UDPSender: Socket closed.")
        self.sock = None
