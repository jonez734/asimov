# demo_udp_sender.py
import argparse
import time
import cv2

from asimov.net import UDPSender, register_packet_type, FramePacket, CAPTURE_WIDTH, CAPTURE_HEIGHT, CAPTURE_FPS, CAPTURE_DEVICE
from asimov import util
from asimov import io

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UDP FRAME Sender")
    parser.add_argument("--host", type=str, default="127.0.0.1",
                        help="The target host to send Frames to (default: %(default)s)")
    parser.add_argument("--port", type=int, default=5000,
                        help="The target port to send Frames to (default: %(default)i)")
    parser.add_argument("--bind-port", type=int, default=0,
                        help="The local port to bind for outgoing packets (0 for OS-assigned, default: %(default)i).")
    parser.add_argument("--capture-device", type=int, default=CAPTURE_DEVICE)
    parser.add_argument("--capture-width", type=int, default=CAPTURE_WIDTH)
    parser.add_argument("--capture-height", type=int, default=CAPTURE_HEIGHT)
    parser.add_argument("--capture-fps", type=int, default=CAPTURE_FPS)
    parser.add_argument("--send_frames", action="store_true", default=True,
                        help="Enable sending of video frames from webcam. If not set, the script will just sleep.")
    parser.add_argument("--frame_interval", type=float, default=1/30.0,
                        help="Target time in seconds between sending frames (default: 1/30.0 for 30 FPS)")
    parser.add_argument("--cols", type=int, default=0,
                        help="Number of grid columns (0 = auto-calculated)")
    parser.add_argument("--rows", type=int, default=0,
                        help="Number of grid rows (0 = auto-calculated)")
    parser.add_argument("--full-frame", action="store_true", default=False,
                        help="Send full frame (not just changed blocks)")
    parser.add_argument("--compress", action="store_true", default=False,
                        help="Enable zlib compression")

    args = parser.parse_args()

    sender = UDPSender(args.host, args.port, args.bind_port)

    cap = None
    if args.send_frames:
        try:
            register_packet_type(FramePacket)
            cap = cv2.VideoCapture(args.capture_device)
            if not cap.isOpened():
                raise IOError("Cannot open webcam.")

            result = util.configure_capture(cap, args.capture_width, args.capture_height, args.capture_fps)
            if result is None:
                raise IOError("Failed to configure capture")
            
            actual_width, actual_height, actual_fps = result
            io.echo(f"Sending to {args.host}:{args.port}")
            io.echo(f"[cap]: Camera {actual_width}x{actual_height} @ {actual_fps} FPS")
            io.echo("Webcam opened successfully.")
            
            sender.prev_frame = None
        except Exception as e:
            io.echo(f"Could not open webcam: {e}. Falling back to sleeping.")
            args.send_frames = False

    last_frame_time = time.time()
    frame_id = 0

    try:
        while True:
            current_time = time.time()

            if args.send_frames:
                if current_time - last_frame_time >= args.frame_interval:
                    ret, frame = cap.read()
                    if not ret:
                        io.echo("Failed to grab frame from camera. Exiting.")
                        break
                    if frame is None:
                        time.sleep(0.01)
                        continue

                    sender.send_frame(
                        frame, 
                        frame_id, 
                        cols=args.cols, 
                        rows=args.rows,
                        full_frame=args.full_frame,
                        compress=args.compress
                    )
                    frame_id += 1
                    last_frame_time = current_time
                time.sleep(0.001)
            else:
                io.echo("[udp_sender] idle")
                time.sleep(1.0)

    except KeyboardInterrupt:
        io.echo("\nSender stopped by user.")
    finally:
        sender.close()
        if cap:
            cap.release()
            io.echo("Webcam released.")
