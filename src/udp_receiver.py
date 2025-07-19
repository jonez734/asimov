# udp_receiver.py
import socket
import argparse
import time

import cv2
import numpy as np

# Import UDPSender from net
from asimov.net import UDPReceiver
from asimov import conf

# --- Callback function to handle complete frames ---
def handle_complete_frame(frame_ndarray: np.ndarray, frame_id: int):
    global last_displayed_frame_id

    display_window_name = "cap"

    # This check is now the responsibility of the external application
    # if it cares about displaying frames in order or avoiding old frames.
    # In net.py, we just provide the complete frame.
    if frame_id > last_displayed_frame_id:
        cv2.imshow(display_window_name, frame_ndarray)
        # We don't need cv2.waitKey(1) here; it's handled in net.py's start_listening loop
        print(f"Displaying frame {frame_id}. Shape: {frame_ndarray.shape}")
        last_displayed_frame_id = frame_id
    else:
        print(f"Received older/duplicate frame {frame_id}. Last displayed was {last_displayed_frame_id}. Skipping display.")

def idle_callback():
    ch = cv2.pollKey() & 0xFF
    if ch == 27 or ch == "q":
        return False
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UDP PING/PONG Receiver")
    parser.add_argument("--host", type=str, default="127.0.0.1",
                        help="The host to listen on (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000,
                        help="The port to listen on (default: 5000)")

    args = parser.parse_args()

    receiver = UDPReceiver(conf.RECEIVER_HOST, conf.RECEIVER_PORT, frame_received_callback=handle_complete_frame, idle_callback=idle_callback)
    try:
        receiver.start_listening()
    finally:
        if receiver:
            receiver.close()
        cv2.destroyAllWindows()
