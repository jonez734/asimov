import cv2
import mediapipe as mp
import numpy as np

MARGIN = 4
DETECTION_INTERVAL = 60

# MediaPipe setup
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.7)

def create_tracker():
    return cv2.TrackerCSRT_create()

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

def get_rotated_polygon(frame, bbox):
    x, y, w, h = [int(v) for v in bbox]
    roi = frame[y:y+h, x:x+w]
    if roi.size == 0:
        # ROI empty, fallback
        return np.array([[x,y],[x+w,y],[x+w,y+h],[x,y+h]])

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 1)
    edges = cv2.Canny(blur, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        cnt = max(contours, key=cv2.contourArea)
        if cv2.contourArea(cnt) > 500:
            rect = cv2.minAreaRect(cnt)
            box = cv2.boxPoints(rect)
            box = np.int0(box)
            box[:, 0] += x
            box[:, 1] += y
            return box

    # fallback to bbox corners if no contour
    return np.array([[x,y],[x+w,y],[x+w,y+h],[x,y+h]])

# --- Main loop ---
cap = cv2.VideoCapture(0)
trackers = []  # list of (tracker, bbox)
frame_counter = 0

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

    # Update trackers
    updated_polygons = []
    new_trackers = []
    for tracker, _ in trackers:
        success, bbox = tracker.update(frame)
        if success:
            poly = get_rotated_polygon(frame, bbox)
            updated_polygons.append(poly)
            new_trackers.append((tracker, bbox))
    trackers = new_trackers

    # Periodically detect new rectangles and reset trackers if none tracked
    if frame_counter % DETECTION_INTERVAL == 0 or len(updated_polygons) == 0:
        new_rectangles = detect_rectangles(frame)
        if new_rectangles:
            trackers = []
            updated_polygons = []
            for (bbox, polygon) in new_rectangles:
                tracker = create_tracker()
                tracker.init(frame, bbox)
                trackers.append((tracker, bbox))
                poly = get_rotated_polygon(frame, bbox)
                updated_polygons.append(poly)

    # Draw polygons and fingertip touch test
    for poly in updated_polygons:
        touching = False
        if left_index_tip:
            dist = cv2.pointPolygonTest(poly, left_index_tip, measureDist=True)
            if dist >= 0:
                touching = True

        color = (0, 255, 0) if touching else (255, 0, 0)
        cv2.polylines(frame, [poly], True, color, 2, lineType=cv2.LINE_AA)

    cv2.imshow("Hybrid Tracker with Rotated Rectangles", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
