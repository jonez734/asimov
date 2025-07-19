# udp_sender.py
import argparse
import time
import cv2

# Import UDPSender from net.py
from asimov.net import UDPSender, register_packet_type, FramePacket
from asimov import conf

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UDP FRAME Sender")
    parser.add_argument("--host", type=str, default="127.0.0.1",
                        help="The target host to send Frames to (default: %(default)s)")
    parser.add_argument("--port", type=int, default=5000,
                        help="The target port to send Frames to (default: %(default)i)")
    parser.add_argument("--bind_port", type=int, default=0,
                        help="The local port to bind for outgoing packets (0 for OS-assigned, default: %(default)i).")
    parser.add_argument("--send_frames", action="store_true", default=True,
                        help="Enable sending of video frames from webcam. If not set, the script will just sleep.")
    # Removed --ping_interval as PINGs will no longer be sent if --send_frames is false.
    parser.add_argument("--frame_interval", type=float, default=1/30.0,
                        help="Target time in seconds between sending frames (default: 1/30.0 for 30 FPS)")
    parser.add_argument("--max_block_side_len", type=int, default=64, # Safer default to avoid IP fragmentation
                        help="Maximum side length for square blocks (e.g., 16, 64). Edge blocks may be smaller. (default: %(default)i)")

    args = parser.parse_args()

    # Initialize UDPSender. It only needs to send now, no specific PONG listening logic needed here.
    sender = UDPSender(args.host, args.port, args.bind_port)

    cap = None
    if args.send_frames:
        try:
            register_packet_type(FramePacket)
            cap = cv2.VideoCapture(0) # 0 for default webcam
            if not cap.isOpened():
                raise IOError("Cannot open webcam.")

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, conf.CAP_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, conf.CAP_HEIGHT)

            # Verify actual camera properties after setting them
            actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = int(cap.get(cv2.CAP_PROP_FPS))

            print(f"[cap]: Camera actual resolution {actual_width}x{actual_height} @ {actual_fps} FPS. sending to {sender}.")

            print("Webcam opened successfully.")
            # Optional: Set webcam resolution
            # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        except Exception as e:
            print(f"Could not open webcam: {e}. Falling back to sleeping.")
            args.send_frames = False # Disable frame sending if webcam fails

    last_frame_time = time.time() # Only track frame time now

    try:
        while True:
            current_time = time.time()

            if args.send_frames:
                # --- Send Frames logic ---
                if current_time - last_frame_time >= args.frame_interval:
                    ret, frame = cap.read()
                    if not ret:
                        print("Failed to grab frame from camera. Exiting.")
                        break
                    if frame is None:
                        time.sleep(0.01)
                        continue

                    sender.send_frame(frame, args.max_block_side_len)
                    last_frame_time = current_time
                time.sleep(0.001) # Small sleep to prevent busy-waiting even when sending frames
            else:
                # --- If not sending frames, just sleep ---
                print("[udp_sender] idle")
                time.sleep(1.0) # Sleep for a longer duration to avoid busy-waiting, e.g., 1 second
                # Or you could just time.sleep(0.001) if you want it to be very responsive to Ctrl+C

    except KeyboardInterrupt:
        print("\nSender stopped by user.")
    finally:
        sender.close()
        if cap:
            cap.release()
            print("Webcam released.")
        # No cv2.destroyAllWindows() needed as this script doesn't call cv2.imshow()
