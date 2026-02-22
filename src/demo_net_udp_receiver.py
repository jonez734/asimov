# demo_net_udp_receiver.py

import argparse
import cv2
import numpy as np

from asimov import io
from asimov.net import UDPReceiver

last_displayed_frame_id = -1


def handle_complete_frame(frame: np.ndarray, frame_id: int):
    global last_displayed_frame_id

    if frame_id > last_displayed_frame_id:
        cv2.imshow("cap", frame)
        io.echo(f"Displaying frame {frame_id}, shape: {frame.shape}")
        last_displayed_frame_id = frame_id
    else:
        io.echo(f"Skipping old frame {frame_id} (last: {last_displayed_frame_id})")


def idle_callback():
    ch = cv2.pollKey() & 0xFF
    if ch == 27 or ch == ord('q'):
        return False
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UDP Frame Receiver")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to listen on")
    parser.add_argument("--port", type=int, default=5000, help="Port to listen on")
    args = parser.parse_args()

    io.echo(f"Listening on {args.host}:{args.port}...")

    receiver = UDPReceiver(
        args.host, 
        args.port, 
        frame_received_callback=handle_complete_frame, 
        idle_callback=idle_callback
    )
    try:
        receiver.start_listening()
    finally:
        receiver.close()
        cv2.destroyAllWindows()
