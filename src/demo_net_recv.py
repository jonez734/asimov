# recv_demo.py

import time
import numpy as np

from net import UDPReceiver, PacketDispatcher, PingPacket, PongPacket, FramePacket
from net import decode_block, display_frame

def handle_ping(packet: PingPacket, addr, receiver: UDPReceiver):
    print(f"Received PING from {addr} (seq={packet.sequence}, ts={packet.timestamp})")
    receiver.send_pong(addr, sequence=packet.sequence)

def handle_pong(packet: PongPacket, addr, receiver: UDPReceiver):
    rtt = time.time() - packet.timestamp
    print(f"Received PONG from {addr} (seq={packet.sequence}) RTT: {rtt:.3f}s")

def handle_frame(packet: FramePacket, addr, receiver: UDPReceiver):
    blocks = [decode_block(b) for b in packet.blocks]
    # assume square layout of blocks
    side = int(len(blocks) ** 0.5)
    h, w = blocks[0].shape[:2]
    full_frame = np.vstack([
        np.hstack(blocks[i * side:(i + 1) * side]) for i in range(side)
    ])
    keep_going = display_frame(full_frame)
    if not keep_going:
        receiver.running = False

def main():
    dispatcher = PacketDispatcher()
    receiver = UDPReceiver(bindaddr=("0.0.0.0", 5000), dispatcher=dispatcher)

    # Register packet handlers
    dispatcher.register_handler("ping", lambda pkt, addr: handle_ping(pkt, addr, receiver))
    dispatcher.register_handler("pong", lambda pkt, addr: handle_pong(pkt, addr, receiver))
    dispatcher.register_handler("frame", lambda pkt, addr: handle_frame(pkt, addr, receiver))

    print("Listening for packets on port 5000...")

    try:
        while receiver.running:
            receiver.receive_once(timeout=1.0)
    finally:
        receiver.close()
        print("Receiver shut down.")

if __name__ == "__main__":
    main()
