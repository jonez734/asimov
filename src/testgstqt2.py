import cv2
import numpy as np

# Set up GStreamer pipeline for sending frames
gst_str = (
    'appsrc ! videoconvert ! video/x-raw,format=I420 ! '
    'x264enc speed-preset=ultrafast tune=zerolatency ! rtph264pay config-interval=1 ! '
    'udpsink host=localhost port=5000'
)

# Open video capture (for example, from webcam or file)
cap = cv2.VideoCapture(1)  # Use '0' for webcam, or replace with a file path

# Set up GStreamer pipeline with VideoWriter
out = cv2.VideoWriter(gst_str, cv2.CAP_GSTREAMER, 0, 30, (640, 480), True)

if not cap.isOpened():
    print("Error: Could not open video source.")
    exit()

if not out.isOpened():
    print("Error: Could not open GStreamer pipeline.")
    exit()

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Send the frame over the GStreamer pipeline
    out.write(frame)

    # Display the frame locally (optional)
    cv2.imshow('Sending to OBS', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release everything when done
cap.release()
out.release()
cv2.destroyAllWindows()
