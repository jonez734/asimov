# demo_net_camera_send.py

import argparse
import cv2
import time
import os
import numpy as np

from asimov import io
from asimov import conf
from asimov.net import UDPSender
from asimov.util import configure_capture

QUIT_FILE = "/tmp/asimov_send_quit"


def generate_test_pattern(width, height, t, frame_id=0, debug=False):
    """Generate an animated test pattern frame based on time t (seconds)."""
    frame = np.zeros((height, width, 3), dtype=np.uint8)

    # Animated gradient background (shifts left-right)
    offset = int((t * 30) % width)
    for x in range(width):
        val = int(((x + offset) % width) * 255 / width)
        frame[:, x, 2] = val

    # Color bars on top (moves up-down)
    bar_height = height // 8
    bar_offset = int(t * 20) % (height + bar_height * 2)
    colors = [
        (255, 255, 255),  # White
        (255, 255, 0),  # Yellow
        (0, 255, 255),  # Cyan
        (0, 255, 0),  # Green
        (255, 0, 255),  # Magenta
        (255, 0, 0),  # Blue
        (0, 0, 255),  # Red
    ]
    for i, color in enumerate(colors):
        y = ((i * bar_height) + bar_offset - bar_height) % (
            height + bar_height
        ) - bar_height
        y_end = min(y + bar_height, height)
        if y < 0:
            frame[0:y_end, :] = color
            frame[max(0, y + bar_height - bar_height) :, :] = color
        else:
            frame[y:y_end, :] = color

    # Bouncing ball
    ball_x = int((t * 50) % (width - 40))
    ball_y = int(abs(np.sin(t * 1.0) * (height - 40)))
    cv2.circle(frame, (ball_x + 20, ball_y + 20), 20, (255, 255, 255), -1)

    # Rotating square in center
    center_x, center_y = width // 2, height // 2
    angle = t * 50
    size = 50
    import math

    x1 = int(center_x + size * math.cos(math.radians(angle)))
    y1 = int(center_y + size * math.sin(math.radians(angle)))
    x2 = int(center_x + size * math.cos(math.radians(angle + 90)))
    y2 = int(center_y + size * math.sin(math.radians(angle + 90)))
    x3 = int(center_x + size * math.cos(math.radians(angle + 180)))
    y3 = int(center_y + size * math.sin(math.radians(angle + 180)))
    x4 = int(center_x + size * math.cos(math.radians(angle + 270)))
    y4 = int(center_y + size * math.sin(math.radians(angle + 270)))
    pts = np.array([[x1, y1], [x2, y2], [x3, y3], [x4, y4]], np.int32)
    cv2.fillPoly(frame, [pts], (255, 0, 0))

    # Frame counter overlay (debug only)
    if debug:
        cv2.rectangle(frame, (5, 5), (220, 40), (0, 0, 0), -1)
        cv2.putText(
            frame,
            f"Frame {frame_id}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )

    return frame


def main():
    parser = argparse.ArgumentParser(description="Send camera via UDP")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Target host")
    parser.add_argument("--port", type=int, default=5000, help="Target port")
    parser.add_argument(
        "--device",
        type=str,
        default=str(conf.CAPTURE_DEVICE),
        help="Camera device (int or path)",
    )
    parser.add_argument(
        "--width", type=int, default=conf.CAPTURE_WIDTH, help="Frame width"
    )
    parser.add_argument(
        "--height", type=int, default=conf.CAPTURE_HEIGHT, help="Frame height"
    )
    parser.add_argument("--fps", type=int, default=conf.CAPTURE_FPS, help="Capture FPS")
    parser.add_argument(
        "--test", action="store_true", help="Use test pattern instead of camera"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Show debug info (frame shape)"
    )
    args = parser.parse_args()

    try:
        device = int(args.device)
    except ValueError:
        device = args.device

    io.echo(f"Sending to {args.host}:{args.port}")

    cap = None
    if not args.test:
        cap = cv2.VideoCapture(device)
        if cap.isOpened():
            result = configure_capture(cap, args.width, args.height, args.fps)
            if result is None:
                io.echo(
                    "Failed to configure capture, falling back to test pattern",
                    level="warn",
                )
                cap.release()
                cap = None
            else:
                actual_w, actual_h, actual_fps = result
                io.echo(f"Camera: {actual_w}x{actual_h} @ {actual_fps} FPS")
        else:
            io.echo("No camera available, falling back to test pattern", level="warn")
            cap = None

    if cap is None:
        io.echo(f"Test pattern: {args.width}x{args.height} @ {args.fps} FPS")

    sender = UDPSender(args.host, args.port)
    sender.prev_frame = None

    io.echo(f"Press ESC to quit, or create {QUIT_FILE} to quit")

    frame_id = 0
    start_time = time.time()
    try:
        while True:
            # Check for quit file
            if os.path.exists(QUIT_FILE):
                os.remove(QUIT_FILE)
                io.echo("Quit file detected")
                break

            if cap is not None:
                ret, frame = cap.read()
                if not ret or frame is None:
                    time.sleep(0.001)
                    continue
            else:
                t = time.time() - start_time
                frame = generate_test_pattern(
                    args.width, args.height, t, frame_id, args.debug
                )
                time.sleep(1.0 / args.fps)

            sender.send_frame(frame, frame_id, full_frame=True)
            frame_id += 1

            cv2.imshow("Send", frame)
            if args.debug:
                io.echo(f"Send: {frame.shape}")
            key = cv2.waitKey(1)
            if key == 27:
                break

    except KeyboardInterrupt:
        io.echo("\nStopped")
    finally:
        sender.close()
        if cap is not None:
            cap.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    exit(main())
