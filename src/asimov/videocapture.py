# asimov/videocapture.py

import cv2
import time
# from multiprocessing import Event

# Import the UDP sender abstraction
from . import conf, net

from bbsengine6 import io

def main(args, inaddr, outaddr):
    """
    Captures video frames from the camera and sends them as chunks over UDP
    to the processing stage using the UDPSender abstraction.
    Frame shape and dtype are assumed to be static (defined in conf).
    """
    cap = cv2.VideoCapture(0) # Initialize video capture from default camera (usually 0)
    if not cap.isOpened():
        print("Error: Could not open video stream in capture process. Signaling stop.")
        stop_e.set() # Signal main process to stop if camera cannot be opened
        return

    # Set camera properties using the arguments passed to the function
    # These arguments are typically sourced from conf.py in main_app.py
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, conf.CAP_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, conf.CAP_HEIght)
    cap.set(cv2.CAP_PROP_FPS, conf.FPS)

    print(f"Capture process started. Attempting to capture at {cap_width}x{cap_height} @ {fps} FPS")

    # Verify actual camera properties after setting them
    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = int(cap.get(cv2.CAP_PROP_FPS))
    print(f"Capture: Camera opened with actual resolution {actual_width}x{actual_height} @ {actual_fps} FPS")

    done = False
    while cap.isOpened():
        ret, frame = cap.read()
        cv2.imshow("frame", frame)
        out.send_frame(frame)
        time.sleep(1/actual_fps)
    print("done")
    return True

##    # Check if the actual captured frame dimensions match the expected STATIC_FRAME_SHAPE
##    # This is a critical check for ensuring compatibility with the UDP protocol's expectations.
##    if (actual_height, actual_width, 3) != net.STATIC_FRAME_SHAPE:
##        print(f"Warning: Camera captured {actual_height}x{actual_width}x3, but STATIC_FRAME_SHAPE is {net.STATIC_FRAME_SHAPE}. "
##              "This may lead to errors if not handled correctly downstream due to unexpected frame dimensions.")

    receiver = net.UDPReceiver(port=0)  # bind to ephemeral port
    local_port = receiver.sock.getsockname()[1]

    sender = net.UDPSender(conf.PROCESSING_HOST, conf.PROCESSING_PORT, bind_port=local_port)

    if not net.wait_for_pong(sender, receiver):
        print("videocapture.100: Failed to receive PONG. Exiting.")
        receiver.close()
        sender.close()
        return

    receiver.close()
    sender.close()
    return

    # Instantiate the UDPSender to send frames to the processing stage
    sender = net.UDPSender(conf.VIDEOCAPTURE_HOST, conf.VIDEOCAPTURE_PORT)

    frame_id_counter = 0 # Counter for unique frame IDs

    try:
        while not stop_e.is_set(): # Loop as long as the stop event is not set
            io.echo(f"videocapture: stop_event is set? {stop_e.is_set()}", level="debug")
            ret, frame = cap.read() # Read a frame from the camera
            if not ret:
                print("Error: Failed to grab frame. Capture process stopping.")
                stop_e.set() # Signal stop on read failure
                break

            # Verify the captured frame's shape and dtype against configured static properties
            if frame.shape != net.STATIC_FRAME_SHAPE or frame.dtype != net.STATIC_FRAME_DTYPE:
                print(f"Warning: Captured frame has unexpected shape {frame.shape} or dtype {frame.dtype}. Expected {net.STATIC_FRAME_SHAPE}, {net.STATIC_FRAME_DTYPE}. Skipping frame.")
                continue # Skip sending this frame if it doesn't match expectations

            try:
                # Use the UDPSender to send the captured frame
                # The sender handles chunking, header packing, and UDP transmission.
                sender.send_frame(frame, frame_id_counter)
            except ConnectionError as e:
                # Catch specific connection errors from the sender (e.g., network issues)
                print(f"Capture: Error sending frame {frame_id_counter}: {e}")
                stop_e.set() # Signal stop on a critical sending error
                break # Exit the loop

            frame_id_counter += 1 # Increment frame ID for the next frame
            # time.sleep(1 / fps) # Introduce a delay to control the output frame rate

    finally:
        cap.release() # Release the camera resource
        print("Capture process detected stop or error. Attempting to send UDP EOS signal.")
        try:
            # Ensure an EOS signal is sent to gracefully shut down the downstream processing stage
            sender.send_eos()
        except ConnectionError as e:
            print(f"Warning: Capture process could not send UDP EOS signal: {e}")
        finally:
            # Always ensure the UDPSender's socket is closed
            sender.close()
        print("Capture process stopped.")
