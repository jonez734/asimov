# udp_receiver.py
import socket
import argparse
import time

import cv2
import numpy as np

# Import UDPSender from net
from asimov.net import UDPReceiver

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UDP PING/PONG Receiver")
    parser.add_argument("--host", type=str, default="127.0.0.1",
                        help="The host to listen on (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000,
                        help="The port to listen on (default: 5000)")

    args = parser.parse_args()

    receiver = UDPReceiver(args.host, args.port)
    try:
        receiver.start_listening()
    finally:
        receiver.close()
