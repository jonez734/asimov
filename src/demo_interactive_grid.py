import cv2
import argparse
from cvzone.HandTrackingModule import HandDetector
from asimov.interactive_grid import InteractiveGrid, DEFAULT_WIDTH, DEFAULT_HEIGHT
from asimov.common import safe_distance
from asimov.gestures import GestureState


# --- Named constants ---
DEFAULT_PINCH_DISTANCE_THRESHOLD = 30   # pixels
DEFAULT_DEBOUNCE_TIME = 0.4             # seconds
DEFAULT_CAMERA_DEVICE_INDEX = 1


def run_demo(camera_index, pinch_threshold, debounce_time):
    """Run the InteractiveGrid hand-tracking demo."""

    # Initialize objects
    grid = InteractiveGrid(singleton_selection=True)
    gestures = GestureState(debounce_time=debounce_time)

    cap = cv2.VideoCapture(camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, DEFAULT_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, DEFAULT_HEIGHT)

    detector = HandDetector(detectionCon=0.8, maxHands=1)

    def on_mouse(event, x, y, flags, param):
        """Mouse fallback for testing."""
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

        hands, _ = detector.findHands(frame, draw=False)
        if hands:
            hand = hands[0]
            tip_index = hand["lmList"][8][:2]
            tip_thumb = hand["lmList"][4][:2]
            fingers = detector.fingersUp(hand)  # [thumb, index, middle, ring, pinky]

            # Hover: index finger only
            if fingers[1] == 1 and sum(fingers) == 1:
                grid.update_hover_by_position(*tip_index)
            else:
                grid.hover_cell = None

            # Pinch: index + thumb
            tip_dist = safe_distance(tip_index, tip_thumb)
            if tip_dist < pinch_threshold:
                if gestures.try_trigger("pinch_click"):
                    grid.handle_click_at_position(*tip_index)

        grid.draw_grid(frame)
        cv2.imshow("InteractiveGrid Demo", frame)

        key = cv2.waitKey(1)
        if key == 27:  # ESC
            break
        elif key == ord("r"):
            grid.reset_grid()

    cap.release()
    cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(
        description="InteractiveGrid demo with hand tracking and pinch gesture."
    )
    parser.add_argument(
        "-c", "--camera", type=int, default=DEFAULT_CAMERA_DEVICE_INDEX,
        help=f"Camera device index (default {DEFAULT_CAMERA_DEVICE_INDEX})"
    )
    parser.add_argument(
        "-p", "--pinch-threshold", type=float, default=DEFAULT_PINCH_DISTANCE_THRESHOLD,
        help=f"Pinch distance threshold in pixels (default {DEFAULT_PINCH_DISTANCE_THRESHOLD})"
    )
    parser.add_argument(
        "-d", "--debounce", type=float, default=DEFAULT_DEBOUNCE_TIME,
        help=f"Debounce time in seconds between gestures (default {DEFAULT_DEBOUNCE_TIME})"
    )
    args = parser.parse_args()

    run_demo(args.camera, args.pinch_threshold, args.debounce)


if __name__ == "__main__":
    main()
