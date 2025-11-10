import cv2
from cvzone.HandTrackingModule import HandDetector
from asimov.interactive_grid import InteractiveGrid
from asimov.interactive_grid import DEFAULT_WIDTH, DEFAULT_HEIGHT
from asimov.common import safe_distance  # import the utility

# --- CONFIG ---
PINCH_DISTANCE_THRESHOLD = 30  # pixels, configurable click threshold

# Create grid (single_selection can be True or False)
grid = InteractiveGrid(singleton_selection=True)

# Initialize webcam
cap = cv2.VideoCapture(1)
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

    # Flip frame if needed
    frame = cv2.flip(frame, 1)

    # Detect hands
    hands, _ = detector.findHands(frame, draw=False)
    if hands:
        hand = hands[0]
        tip_index = hand["lmList"][8][:2]   # index fingertip
        tip_middle = hand["lmList"][12][:2] # middle fingertip

        # Hover updates based on fingertip position
        grid.update_hover_by_position(*tip_index)

        # Pinch/click detection
        tip_dist = safe_distance(tip_index, tip_middle)
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
