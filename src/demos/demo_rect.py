import cv2
import numpy as np
import time
import argparse
from asimov import rect  # adjust if your module path differs

# Canvas size if not using webcam
WIDTH, HEIGHT = 640, 480


def draw_rectangles(img, context):
    """Draw rectangles on the image. Converts normalized coords to pixel coords."""
    h, w = img.shape[:2]
    for r in context.get("rectangles", []):
        poly = [(int(x * w), int(y * h)) for x, y in r["polygon"]]

        # Skip polygons that are degenerate or too small
        if len(poly) < 4 or cv2.contourArea(np.array(poly, np.int32)) < 10:
            continue

        poly_np = np.array(poly, np.int32).reshape((-1, 1, 2))
        color = (0, 255, 0) if r["touched"] else (0, 0, 255)
        thickness = max(2, int(min(w, h) * 0.002))  # ensure visible line
        cv2.polylines(img, [poly_np], isClosed=True, color=color, thickness=thickness)

        if r.get("label"):
            cv2.putText(
                img, str(r["label"]), poly[0], cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2
            )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--webcam", action="store_true", help="Use webcam instead of blank canvas"
    )
    args = parser.parse_args()

    context = {}
    rect.init_context(context)

    # Example rectangles (coordinates are canvas pixels)
    rect.add(
        context, [(50, 50), (150, 50), (150, 150), (50, 150)], timeout=5, label="A"
    )
    rect.add(
        context, [(200, 100), (300, 100), (300, 200), (200, 200)], timeout=8, label="B"
    )
    rect.add(
        context, [(400, 50), (500, 50), (500, 150), (400, 150)], timeout=3, label="C"
    )

    if args.webcam:
        cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            print("Cannot open webcam")
            return
    else:
        cap = None

    cv2.namedWindow("Rect Demo")
    last_update = time.time()

    while True:
        if cap:
            ret, img = cap.read()
            if not ret:
                print("Failed to grab frame from webcam")
                break
            img = cv2.resize(img, (WIDTH, HEIGHT))
        else:
            img = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)

        # Expire old rectangles every 0.1 seconds
        if time.time() - last_update > 0.1:
            rect.update_context(context)
            last_update = time.time()

        # Draw rectangles
        draw_rectangles(img, context)

        cv2.imshow("Rect Demo", img)
        key = cv2.waitKey(50) & 0xFF

        if key == ord("q"):
            break
        if key == ord("t") and context["rectangles"]:
            rect.mark_touched(context, 0)

    if cap:
        cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
