# demo_net_receive_frame.py

import argparse
import cv2
import numpy as np

from asimov import io
from asimov.net import UDPReceiver, TCPReceiver

DEFAULT_PORT = 5000


def main():
    parser = argparse.ArgumentParser(description="Receive cv2 frames over network")
    parser.add_argument(
        "--protocol",
        type=str,
        default="udp",
        choices=["tcp", "udp"],
        help="Protocol to use (tcp or udp)",
    )
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to")
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help="Port to listen on"
    )
    args = parser.parse_args()

    if args.protocol == "tcp":
        receiver = TCPReceiver(args.host, args.port, blocking=False, timeout=1.0)
    else:
        receiver = UDPReceiver(args.host, args.port, blocking=False, timeout=1.0)

    io.echo(f"Listening on {args.host}:{args.port} via {args.protocol.upper()}...")

    first_packet_received = False
    try:
        while True:
            result = receiver.receive()

            if result is None:
                continue

            if not first_packet_received:
                io.echo("Received first packet!")
                first_packet_received = True

            if result is None or not isinstance(result, np.ndarray):
                continue

            io.echo(f"Received frame ({result.shape})")

            cv2.imshow("Received Frame", result)
            if cv2.waitKey(1) == 27:
                break

    finally:
        receiver.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
