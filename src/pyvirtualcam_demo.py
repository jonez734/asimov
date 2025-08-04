import cv2
import pyvirtualcam
import numpy as np

import mediapipe as mp

# Constants
MARGIN = 20  # pixels

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.7)

index_finger_tip = None

def detect_rectangles(frame):
    detected = []
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 1)
    canny = cv2.Canny(blur, 50, 150)
    contours, _ = cv2.findContours(canny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 1000:
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
            if len(approx) == 4:
                polygon = approx.reshape((4, 2))
                detected.append(polygon)
    return detected

def draw_rectangles(frame, rectangles):
    global index_finger_tip
    for polygon in rectangles:
        poly_np = np.array(polygon, dtype=np.int32).reshape((-1, 1, 2))
        touching = False
        if index_finger_tip:
            dist = cv2.pointPolygonTest(poly_np, finger_tip, False)
            if dist >= -MARGIN:
                touching = True

        color = (0, 255, 0) if touching else (255, 0, 0)
        cv2.polylines(frame, [poly_np], True, color, 2)
    return frame

def detect_index_finger_tips(frame):
    global index_finger_tip

    results = hands.process(frame)
    index_finger_tip = None

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            h, w, _ = frame.shape
            x = int(hand_landmarks.landmark[8].x * w)  # Index finger tip
            y = int(hand_landmarks.landmark[8].y * h)
            index_finger_tip = (x, y)
            cv2.circle(frame, index_finger_tip, 8, (0, 255, 255), -1)

    return frame

# Open the real webcam
cap = cv2.VideoCapture(0)

# Make sure the webcam opens correctly
if not cap.isOpened():
    raise RuntimeError("Could not open webcam")

# Get the frame size
ret, frame = cap.read()
if not ret:
    raise RuntimeError("Failed to read frame from webcam")

height, width = frame.shape[:2]

# Start the virtual camera
with pyvirtualcam.Camera(width=width, height=height, fps=30) as cam:
    print(f'Virtual camera running: {cam.device}')
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)

        # Optional: draw something on the frame
        cv2.putText(frame, "asimov demo v202505.0", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

        frame = detect_index_finger_tips(frame)
        rectangles = detect_rectangles(frame)
        frame = draw_rectangles(frame, rectangles)
        

        cv2.imshow("asimov demo", frame)

        # Send frame to virtual camera
        cam.send(frame)

        ch = cv2.waitKey(1) & 0xFF
        if ch == ord("q") or ch == 27:
            break

        # Wait until next frame is due
        cam.sleep_until_next_frame()
