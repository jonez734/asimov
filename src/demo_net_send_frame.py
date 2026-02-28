# send_frame_demo.py

import argparse
import cv2
import time
from asimov.net import UDPSender, TCPSender
from asimov import util
from asimov import io


def main():
    parser = argparse.ArgumentParser(description="Send cv2 frames over UDP")
    parser.add_argument(
        "--protocol",
        type=str,
        default="udp",
        choices=["tcp", "udp"],
        help="Protocol to use (tcp or udp)",
    )
    util.add_camera_args(parser, hidden=True)
    util.add_network_args(parser)
    args = parser.parse_args()

    if args.protocol == "tcp":
        sender = TCPSender(args.host, args.port)
    else:
        sender = UDPSender(args.host, args.port)
    cap = cv2.VideoCapture(args.capture_device)

    if not cap.isOpened():
        io.echo("Unable to open camera.")
        return

    result = util.configure_capture(
        cap, args.capture_width, args.capture_height, args.capture_fps
    )
    if result is None:
        io.echo("Failed to configure capture")
        return

    actual_width, actual_height, actual_fps = result
    io.echo(f"Sending to {args.host}:{args.port} via {args.protocol.upper()}")
    io.echo(f"Capture: {actual_width}x{actual_height} @ {actual_fps} FPS")

    sender.prev_frame = None
    frame_id = 0
    try:
        while True:
            ret, frame = cap.read()
            if frame is None:
                time.sleep(0.001)
                continue

            if not ret:
                io.echo("Unable to read frame.")
                break

            sender.send_frame(
                frame,
                frame_id,
                cols=args.cols,
                rows=args.rows,
                full_frame=args.full_frame,
                compress=args.compress,
            )
            frame_id += 1

            # Optional: show frame locally for debugging
            cv2.imshow("Sending Frame", frame)
            if cv2.waitKey(1) == 27:  # ESC to quit
                break

            time.sleep(0.01)  # Throttle the send loop slightly
    finally:
        cap.release()
        sender.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
