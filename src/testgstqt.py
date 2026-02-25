import cv2

# GStreamer pipeline to send video to UDP for OBS
gst_pipeline = "appsrc ! videoconvert ! x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! rtph264pay config-interval=1 ! udpsink host=localhost port=5000"

# Initialize video capture (use 0 for the default camera or specify a file)
cap = cv2.VideoCapture(1)

# Check if camera opened successfully
if not cap.isOpened():
    print("Error: Could not open video stream.")
    exit()

# Define the GStreamer video writer with the correct format
out = cv2.VideoWriter(gst_pipeline, cv2.CAP_GSTREAMER, 0, 30.0, (640, 480))

if not out.isOpened():
    print("Error: Could not open GStreamer pipeline.")
    cap.release()
    exit()

# Capture and send video frames
while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Failed to capture frame.")
        break

    # Write frame to GStreamer pipeline
    out.write(frame)

    # Display the frame locally (optional)
    cv2.imshow('Frame', frame)

    # Press 'q' to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release everything
cap.release()
out.release()
cv2.destroyAllWindows()
