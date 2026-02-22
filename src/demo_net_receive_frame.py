# demo_net_receive_frame.py

import argparse
import cv2

from asimov import io
from asimov.net import UDPReceiver

DEFAULT_PORT = 5000

def main():
    parser = argparse.ArgumentParser(description="Receive cv2 frames over UDP")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to listen on")
    args = parser.parse_args()

    receiver = UDPReceiver(args.host, args.port, blocking=False, timeout=1.0)

    io.echo(f"Listening on {args.host}:{args.port}...")

    try:
        while True:
            result = receiver.receive()
            
            if result is None:
                continue
            
            if hasattr(result, 'frame_id'):
                packet = result
            else:
                continue

            io.echo(f"Received frame {packet.frame_id}")

    finally:
        receiver.close()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
