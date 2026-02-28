import cv2
import subprocess

# Define the GStreamer pipeline for sending video over UDP
gst_pipeline = (
    "appsrc ! videoconvert ! x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! "
    "rtph264pay config-interval=1 ! udpsink host=localhost port=5000"
)

# Open the video capture (use 0 for default webcam)
cap = cv2.VideoCapture(1)

# Check if the camera opened successfully
if not cap.isOpened():
    print("Error: Could not open video capture.")
    exit()

# Get the width and height of the video capture
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# Start the GStreamer pipeline using subprocess
gst_process = subprocess.Popen(
    ['gst-launch-1.0', '-v', 'appsrc', '!',
     'videoconvert', '!',
     'x264enc', 'tune=zerolatency', 'bitrate=500', 'speed-preset=superfast', '!',
     'rtph264pay', 'config-interval=1', '!',
     'udpsink', 'host=localhost', 'port=5000'],
    stdin=subprocess.PIPE
)

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Failed to capture frame.")
        break

    # Convert the frame to a format suitable for GStreamer (BGR to RGB)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Write the frame to GStreamer stdin
    gst_process.stdin.write(rgb_frame.tobytes())

    # Display the frame locally (optional)
    cv2.imshow("Frame", frame)

    # Press 'q' to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the video capture
cap.release()

# Close GStreamer pipeline
gst_process.stdin.close()
gst_process.wait()

cv2.destroyAllWindows()
