# File: demo_interactive_grid.py

import cv2
import argparse
from asimov.interactive_grid import InteractiveGrid

# -----------------------------
# Named constants
# -----------------------------
CAMERA_INDEX = 1
FRAME_WIDTH = 1024
FRAME_HEIGHT = 768

# -----------------------------
# Global mouse state
# -----------------------------
mouse_pos = [None, None]
mouse_clicked = False


def mouse_callback(event, x, y, flags, param):
    """Update mouse hover and detect clicks."""
    global mouse_pos, mouse_clicked
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
    # Interactive grid
    # -----------------------------
    grid = InteractiveGrid(
        rows=args.rows,
        cols=args.cols,
        singleton_selection=args.singleton,
        frame_width=args.width,
        frame_height=args.height,
    )

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
        # Update grid (handles hand & mouse)
        # -----------------------------
        grid.update(frame, mouse_pos, mouse_clicked)
        mouse_clicked = False  # reset click state

        # -----------------------------
        # Draw the grid
        # -----------------------------
        grid.draw_grid(frame)

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
