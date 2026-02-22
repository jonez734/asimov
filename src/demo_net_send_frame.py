# send_frame_demo.py

import argparse
import cv2
import time
from asimov.net import UDPSender
from asimov.net import CAPTURE_WIDTH, CAPTURE_HEIGHT, CAPTURE_FPS, CAPTURE_DEVICE
from asimov import util
from asimov import io


def main():
    parser = argparse.ArgumentParser(description="Send cv2 frames over UDP")
    parser.add_argument("--capture-device", type=int, default=CAPTURE_DEVICE)
    parser.add_argument("--capture-width", type=int, default=CAPTURE_WIDTH)
    parser.add_argument("--capture-height", type=int, default=CAPTURE_HEIGHT)
    parser.add_argument("--capture-fps", type=int, default=CAPTURE_FPS)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--cols", type=int, default=0, help="Grid columns (0=auto)")
    parser.add_argument("--rows", type=int, default=0, help="Grid rows (0=auto)")
    parser.add_argument("--full-frame", action="store_true", help="Send full frame (not just changes)")
    parser.add_argument("--compress", action="store_true", help="Enable zlib compression")
    args = parser.parse_args()

    sender = UDPSender(args.host, args.port)
    cap = cv2.VideoCapture(args.capture_device)

    if not cap.isOpened():
        io.echo("Unable to open camera.")
        return

    result = util.configure_capture(cap, args.capture_width, args.capture_height, args.capture_fps)
    if result is None:
        io.echo("Failed to configure capture")
        return
    
    actual_width, actual_height, actual_fps = result
    io.echo(f"Sending to {args.host}:{args.port}")
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
                compress=args.compress
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
