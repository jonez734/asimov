# import cvzone
# from cvzone.FPS import FPS as cvzoneFPS
# from cvzone.HandTrackingModule import HandDetector

import cv2
import gi
import time

gi.require_version("Gst", "1.0")
from gi.repository import Gst

from cvzone.FPS import FPS as cvzoneFPS
from cvzone.HandTrackingModule import HandDetector

RESOLUTION = (640, 480)
# RESOLUTION = (1280, 720)
SRC = 1
FONT = cv2.FONT_HERSHEY_SIMPLEX
FPS = 20

LABELCOLOR = (187, 187, 187)  # lightgray
VALUECOLOR = (0, 204, 85)  # green
DARKGRAY = (51, 51, 51)
BGCOLOR = DARKGRAY
GREEN = (0, 204, 85)
CONTOURCOLOR = GREEN
VIDEODEVICE = 1
# Initialize GStreamer
Gst.init(None)

# Define the GStreamer pipeline
pipeline = Gst.parse_launch(
    "appsrc name=source ! videoconvert ! x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! "
    "queue ! rtph264pay config-interval=1 ! udpsink host=localhost port=5005"
)

# Retrieve the appsrc element
appsrc = pipeline.get_by_name("source")

# Set the caps (capabilities) for the video stream
appsrc.set_property(
    "caps",
    Gst.Caps.from_string(
        f"video/x-raw,format=BGR,width={RESOLUTION[0]},height={RESOLUTION[1]},framerate={FPS}/1"
    ),
)

appsrc.set_property("is-live", True)  # Indicate that the source is live
appsrc.set_property("block", False)  # Non-blocking behavior
appsrc.set_property("format", Gst.Format.TIME)  # Use time format for timestamps


def probe_buffer(appsrc, buf):
    print(f"Pushing buffer with PTS: {buf.pts} and duration: {buf.duration}")
    return Gst.FlowReturn.OK


# appsrc.connect("push-buffer", probe_buffer)

# Start the GStreamer pipeline
pipeline.set_state(Gst.State.PLAYING)

# Create a new segment event
segment = Gst.Segment()
segment.init(Gst.Format.TIME)
segment.start = 0  # Start time
segment.time = 0  # Time for the segment
segment.duration = Gst.CLOCK_TIME_NONE  # Duration for the segment (unknown initially)

# Send the segment event to the pipeline
appsrc.send_event(Gst.Event.new_segment(segment))

# Open the video capture (0 for default webcam)
cap = cv2.VideoCapture(1)

# Check if the camera opened successfully
if not cap.isOpened():
    print("Error: Could not open video capture.")
    exit()


# Define a helper function to push frames into the GStreamer pipeline
def send_frame(frame, pts):
    # Create a buffer and fill it with the frame data
    data = frame.tobytes()
    buf = Gst.Buffer.new_allocate(None, len(data), None)
    buf.fill(0, data)
    current_time = int(time.time() * Gst.SECOND)  # Convert to nanoseconds
    buf.pts = current_time
    buf.dts = current_time
    buf.duration = Gst.SECOND // FPS  # Assuming 30 FPS

    # Set the presentation timestamp (pts) and duration for the buffer
    buf.pts = pts
    buf.duration = Gst.util_uint64_scale(1, Gst.SECOND, FPS)  # 30 fps

    # Push the buffer into the pipeline
    appsrc.emit("push-buffer", buf)


# Frame counter to keep track of time for the PTS
frame_count = 0


# Function to handle GStreamer bus messages
def on_bus_message(bus, message):
    msg_type = message.type
    if msg_type == Gst.MessageType.EOS:
        print("End-Of-Stream reached.")
        return Gst.BusSyncReply.PASS
    elif msg_type == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        print(f"Error: {err}, {debug}")
        return Gst.BusSyncReply.PASS
    return Gst.BusSyncReply.PASS


# Add a bus to the pipeline
bus = pipeline.get_bus()
bus.add_signal_watch()
bus.connect("message", on_bus_message)

fpsReader = cvzoneFPS(avgCount=FPS)


class handHandler(object):
    def __init__(self):
        self.detector = HandDetector(
            staticMode=False,
            maxHands=2,
            modelComplexity=1,
            detectionCon=0.5,
            minTrackCon=0.3,
        )

    def handle(self, image, draw=True):
        hands, image = self.detector.findHands(image, draw=draw, flipType=True)
        if hands == [] or hands is None:
            return image

        for h in hands:
            lmList = h["lmList"]
            fingers = self.detector.fingersUp(h)
            print(f"{fingers=}")
            if fingers == [0, 1, 0, 0, 0] or fingers == [1, 1, 0, 0, 0]:
                print("index finger up")
        return image


hh = handHandler()

# Main loop for OpenCV capture and GStreamer frame sending
while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Failed to capture frame.")
        break

    # Calculate the PTS (Presentation Time Stamp) for the frame
    pts = frame_count * Gst.util_uint64_scale(1, Gst.SECOND, FPS)

    #    frame = hh.handle(frame, draw=True)

    # Send the frame to GStreamer
    send_frame(frame, pts)

    fps, frame = fpsReader.update(
        frame, bgColor=BGCOLOR, textColor=VALUECOLOR, scale=2, thickness=2
    )

    # Display the frame locally (optional)
    cv2.imshow("Frame", frame)

    # Handle OpenCV window events and exit on 'q' or ESC
    ch = cv2.waitKey(1) & 0xFF
    if ch == 27 or ch == ord("q"):
        break

    #    fps, frame = fpsReader.update(frame, bgColor=libasimov.BGCOLOR, textColor=libasimov.VALUECOLOR, scale=3, thickness=3)

    # Increment the frame count
    frame_count += 1

    # Introduce a small delay (sleep for 33ms to match ~30 FPS)
    time.sleep(0.033)

# Stop the pipeline and end the stream
appsrc.emit("end-of-stream")
pipeline.set_state(Gst.State.NULL)

# Release resources
cap.release()
cv2.destroyAllWindows()
