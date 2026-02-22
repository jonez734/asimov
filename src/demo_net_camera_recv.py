# demo_net_camera_recv.py

import argparse
import os
import time
import cv2
import numpy as np

from asimov import io
from asimov.net import UDPReceiver


last_frame_id = -1
QUIT_FILE = "/tmp/asimov_recv_quit"


def main():
    parser = argparse.ArgumentParser(description="Receive camera via UDP")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=5000, help="Bind port")
    parser.add_argument(
        "--debug", action="store_true", help="Show debug info (frame shape)"
    )
    args = parser.parse_args()

    io.echo(f"Listening on {args.host}:{args.port}")
    io.echo(f"Press ESC or 'q' to quit, or create {QUIT_FILE} to quit")

    receiver = UDPReceiver(args.host, args.port, blocking=False, timeout=1.0)

    start_time = time.time()

    try:
        while True:
            # Check for quit file
            if os.path.exists(QUIT_FILE):
                os.remove(QUIT_FILE)
                io.echo("Quit file detected")
                break

            result = receiver.receive()

            if isinstance(result, np.ndarray):
                global last_frame_id
                last_frame_id += 1
                elapsed = time.time() - start_time
                if args.debug:
                    io.echo(f"Recv: {result.shape}")
                    cv2.rectangle(result, (5, 5), (220, 40), (0, 0, 0), -1)
                    cv2.putText(
                        result,
                        f"F:{last_frame_id} T:{elapsed:.1f}s",
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 0),
                        2,
                    )
                cv2.imshow("Recv", result)

            key = cv2.waitKey(1)
            if key == 27 or key == ord("q"):
                break

            if isinstance(result, np.ndarray):
                io.echo(f"Frame {last_frame_id}")

    except KeyboardInterrupt:
        io.echo("\nStopped")
    finally:
        receiver.close()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    exit(main())
