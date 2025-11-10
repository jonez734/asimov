import cv2
from cvzone.HandTrackingModule import HandDetector
from asimov.interactive_grid import InteractiveGrid
from asimov.interactive_grid import DEFAULT_WIDTH, DEFAULT_HEIGHT
from asimov.common import safe_distance

# --- CONFIG ---
CAMERA_DEVICE_INDEX = 1             # camera device index
PINCH_DISTANCE_THRESHOLD = 30       # pixels, configurable click threshold

# Create grid with singleton selection
grid = InteractiveGrid(singleton_selection=True)

# Initialize webcam
cap = cv2.VideoCapture(CAMERA_DEVICE_INDEX)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, DEFAULT_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, DEFAULT_HEIGHT)

# Initialize hand detector
detector = HandDetector(detectionCon=0.8, maxHands=1)

def on_mouse(event, x, y, flags, param):
    """Mouse fallback: update hover and click."""
    if event == cv2.EVENT_LBUTTONDOWN:
        grid.handle_click_at_position(x, y)
    grid.update_hover_by_position(x, y)

cv2.namedWindow("InteractiveGrid Demo")
cv2.setMouseCallback("InteractiveGrid Demo", on_mouse)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)

    # Detect hands
    hands, _ = detector.findHands(frame, draw=False)
    if hands:
        hand = hands[0]
        tip_index = hand["lmList"][8][:2]  # index fingertip
        tip_thumb = hand["lmList"][4][:2]  # thumb tip

        # Get fingers state from detector
        fingers = detector.fingersUp(hand)  # [thumb, index, middle, ring, pinky]

        # --- Hover: only when index finger is up alone ---
        if fingers[1] == 1 and sum(fingers) == 1:
            grid.update_hover_by_position(*tip_index)
        else:
            grid.hover_cell = None  # remove hover

        # --- Pinch/Click: distance between index and thumb ---
        if fingers[0] == 1 and fingers[1] == 1 and sum(fingers) == 2:
            tip_dist = safe_distance(tip_index, tip_thumb)
            if tip_dist < PINCH_DISTANCE_THRESHOLD:
                grid.handle_click_at_position(*tip_index)

    # Draw grid overlay
    grid.draw_grid(frame)

    cv2.imshow("InteractiveGrid Demo", frame)
    key = cv2.waitKey(1)
    if key == 27:  # ESC
        break
    elif key == ord('r'):
        grid.reset_grid()

cap.release()
cv2.destroyAllWindows()
