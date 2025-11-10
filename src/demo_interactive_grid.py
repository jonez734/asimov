import cv2

from asimov.interactive_grid import InteractiveGrid
from asimov.interactive_grid import DEFAULT_WIDTH, DEFAULT_HEIGHT

def main():
    grid = InteractiveGrid()

    # Initialize webcam
    cap = cv2.VideoCapture(1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, DEFAULT_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, DEFAULT_HEIGHT)

    cv2.namedWindow("InteractiveGrid Demo")
    cv2.setMouseCallback("InteractiveGrid Demo", grid.handle_mouse_event)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        grid.draw_grid(frame)
        cv2.imshow("InteractiveGrid Demo", frame)

        key = cv2.waitKey(1)
        if key == 27:  # ESC
            break
        elif key == ord('r'):
            grid.reset_grid()

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
