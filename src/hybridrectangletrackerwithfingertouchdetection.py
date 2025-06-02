import cv2
import mediapipe as mp
import numpy as np

MARGIN = 20
DETECTION_INTERVAL = 60

# MediaPipe setup
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.7)

# Tracker creator
def create_tracker():
    return cv2.TrackerCSRT_create()

# Video capture
cap = cv2.VideoCapture(0)
trackers = []  # list of (tracker, bbox)
frame_counter = 0

def detect_rectangles(frame):
    rectangles = []
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
                x, y, w, h = cv2.boundingRect(polygon)
                rectangles.append(((x, y, w, h), polygon))
    return rectangles

while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame_counter += 1

    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(img_rgb)

    left_index_tip = None
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            h, w, _ = frame.shape
            x = int(hand_landmarks.landmark[8].x * w)
            y = int(hand_landmarks.landmark[8].y * h)
            left_index_tip = (x, y)
            cv2.circle(frame, left_index_tip, 8, (0, 255, 255), -1)

    # Update all trackers manually
    updated_polygons = []
    new_trackers = []
    for tracker, _ in trackers:
        success, bbox = tracker.update(frame)
        if success:
            x, y, w, h = [int(v) for v in bbox]
            poly = np.array([
                [[x, y]],
                [[x + w, y]],
                [[x + w, y + h]],
                [[x, y + h]]
            ], dtype=np.int32)
            updated_polygons.append(poly)
            new_trackers.append((tracker, bbox))  # keep successful tracker

    trackers = new_trackers

    # Re-detect rectangles periodically or if tracking is lost
    if frame_counter % DETECTION_INTERVAL == 0 or len(updated_polygons) == 0:
        new_rectangles = detect_rectangles(frame)
        if new_rectangles:
            trackers = []
            updated_polygons = []
            for (bbox, polygon) in new_rectangles:
                tracker = create_tracker()
                tracker.init(frame, bbox)
                trackers.append((tracker, bbox))
                x, y, w, h = bbox
                poly = np.array([
                    [[x, y]],
                    [[x + w, y]],
                    [[x + w, y + h]],
                    [[x, y + h]]
                ], dtype=np.int32)
                updated_polygons.append(poly)

    # Draw all polygons and check fingertip proximity
    for poly in updated_polygons:
        touching = False
        if left_index_tip:
            dist = cv2.pointPolygonTest(poly, left_index_tip, False)
            if dist >= -MARGIN:
                touching = True
        color = (0, 255, 0) if touching else (255, 0, 0)
        cv2.polylines(frame, [poly], True, color, 2)

    cv2.imshow("Manual Hybrid Tracker", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
