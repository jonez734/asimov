# File: demo_interactive_grid.py

import cv2
import argparse
from cvzone.HandTrackingModule import HandDetector
from asimov.interactive_grid import InteractiveGrid
from asimov.common import safe_distance

# -----------------------------
# Named constants
# -----------------------------
CAMERA_INDEX = 1
FRAME_WIDTH = 1024
FRAME_HEIGHT = 768
MAX_HANDS = 1
DETECTION_CONFIDENCE = 0.8
PINCH_DISTANCE_THRESHOLD = 40
INDEX_ONLY_GESTURE = [False, True, False, False, False]

# -----------------------------
# Global mouse state
# -----------------------------
mouse_pos = [None, None]
mouse_clicked = False

def mouse_callback(event, x, y, flags, param):
    """Update mouse hover and detect clicks."""
    global mouse_clicked
    if event == cv2.EVENT_MOUSEMOVE:
        mouse_pos[0] = x
        mouse_pos[1] = y
    elif event == cv2.EVENT_LBUTTONDOWN:
        mouse_clicked = True


def main():
    global mouse_clicked

    parser = argparse.ArgumentParser(description="Interactive Grid Demo")
    parser.add_argument("--camera", type=int, default=CAMERA_INDEX)
    parser.add_argument("--width", type=int, default=FRAME_WIDTH)
    parser.add_argument("--height", type=int, default=FRAME_HEIGHT)
    parser.add_argument("--rows", type=int, default=2)
    parser.add_argument("--cols", type=int, default=2)
    parser.add_argument("--singleton", action="store_true")
    args = parser.parse_args()

    # -----------------------------
    # Video capture
    # -----------------------------
    cap = cv2.VideoCapture(args.camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    # -----------------------------
    # Hand detector
    # -----------------------------
    detector = HandDetector(maxHands=MAX_HANDS, detectionCon=DETECTION_CONFIDENCE)

    # -----------------------------
    # Interactive grid
    # -----------------------------
    grid = InteractiveGrid(rows=args.rows, cols=args.cols, singleton_selection=args.singleton)

    # -----------------------------
    # Setup mouse callback
    # -----------------------------
    cv2.namedWindow("Interactive Grid")
    cv2.setMouseCallback("Interactive Grid", mouse_callback)

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frame = cv2.flip(frame, 1)  # mirror for natural interaction

        # -----------------------------
        # Detect hands once (draw=False)
        # -----------------------------
        hands, _ = detector.findHands(frame, draw=False)

        # Hover and pinch tracking
        hover_updated = False
        pinch_cell = None

        if hands:
            hand = hands[0]
            lmList = hand["lmList"]
            fingers = detector.fingersUp(hand)
            index_tip = lmList[8]
            thumb_tip = lmList[4]
            px, py = int(index_tip[0]), int(index_tip[1])

            # Hover from hand only if index finger is the only one extended
            if fingers == INDEX_ONLY_GESTURE:
                grid.update_hover_by_position(px, py, frame.shape[1], frame.shape[0])
                hover_updated = True

            # Selection from hand
            grid.attempt_select(fingers, px, py, frame.shape[1], frame.shape[0])

            # Pinch detection
            dist = safe_distance(index_tip, thumb_tip)
            if dist < PINCH_DISTANCE_THRESHOLD:
                pinch_cell = grid.get_cell_from_position(px, py, frame.shape[1], frame.shape[0])

        # Mouse hover if hand did not update
        if not hover_updated:
            if mouse_pos[0] is not None and mouse_pos[1] is not None:
                grid.update_hover_by_position(mouse_pos[0], mouse_pos[1], frame.shape[1], frame.shape[0])
            else:
                grid.update_hover_by_position(None, None)

        # Mouse click selection
        if mouse_clicked and mouse_pos[0] is not None and mouse_pos[1] is not None:
            grid.attempt_select(INDEX_ONLY_GESTURE, mouse_pos[0], mouse_pos[1],
                                frame.shape[1], frame.shape[0])
            mouse_clicked = False

        # Update pinch
        grid.pinch_cell = pinch_cell

        # -----------------------------
        # Draw grid first
        # -----------------------------
        grid.draw_grid(frame)

        # -----------------------------
        # Draw hands on top
        # -----------------------------
        detector.findHands(frame, draw=True)

        # -----------------------------
        # Display
        # -----------------------------
        cv2.imshow("Interactive Grid", frame)
        if cv2.waitKey(1) & 0xFF == 27:  # ESC to exit
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
