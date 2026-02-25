# demo.py
import argparse
import time
import cv2
import numpy as np
from asimov import rect  # expects asimov/rect.py from above

# Detection/selection parameters (tweak as needed)
TARGET_ASPECT = 1.4    # desired width/height
EPS_ASPECT = 0.25      # allowed aspect deviation
TARGET_AREA = 1000     # desired area in pixels
EPS_AREA = 800         # allowed area deviation
MERGE_EPSILON = 0.05   # normalized coords closeness for merge
DETECT_TIMEOUT = 3.0   # stickiness in seconds when newly detected
MIN_DRAW_AREA_PX = 50  # minimum pixel area to draw (avoid tiny artifacts)

# Default canvas size (used only when no webcam)
WIDTH, HEIGHT = 640, 480


# ---------------------------
# Helper: order polygon points
# ---------------------------
def order_points(pts):
    """Return points in order: top-left, top-right, bottom-right, bottom-left"""
    # pts: numpy array shape (4,2)
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


# ---------------------------
# Detection (OpenCV) - demo side
# ---------------------------
def detect_from_frame(frame,
                      target_aspect=TARGET_ASPECT,
                      eps_aspect=EPS_ASPECT,
                      target_area=TARGET_AREA,
                      eps_area=EPS_AREA):
    """
    Detect quadrilateral contours that match aspect / area constraints.
    Returns list of polygons with normalized coordinates [(x,y), ...].
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # Adaptive thresholding is sometimes more robust across lighting
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    h, w = frame.shape[:2]
    out = []

    for cnt in contours:
        # bounding box and raw area in pixels
        bx, by, bw, bh = cv2.boundingRect(cnt)
        if bh == 0:
            continue
        aspect = float(bw) / float(bh)
        area = bw * bh

        # filter by aspect and area (pixel area)
        if abs(aspect - target_aspect) > eps_aspect:
            continue
        if abs(area - target_area) > eps_area:
            continue

        # polygon approximation
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)

        if len(approx) != 4:
            continue

        pts = np.array([p[0] for p in approx], dtype=np.float32)
        ordered = order_points(pts)
        # Normalize coordinates (0..1)
        poly_norm = [ (float(px) / w, float(py) / h) for (px, py) in ordered ]
        out.append(poly_norm)

    return out


# ---------------------------
# Drawing helper (demo.py)
# ---------------------------
def draw_rectangles(img, context):
    """
    Draw rectangles stored in context["rectangles"] on the image.
    Skips degenerate or tiny polygons.
    """
    h, w = img.shape[:2]
    thickness = max(2, int(min(w, h) * 0.002))

    for r in context.get("rectangles", []):
        poly_norm = r.get("polygon", [])
        if not poly_norm or len(poly_norm) < 4:
            continue

        poly_px = [ (int(x * w), int(y * h)) for (x, y) in poly_norm ]

        # skip if the polygon has effectively zero area
        contour_np = np.array(poly_px, dtype=np.int32)
        if abs(cv2.contourArea(contour_np)) < MIN_DRAW_AREA_PX:
            continue

        color = (0, 255, 0) if r.get("touched") else (0, 0, 255)
        cv2.polylines(img, [contour_np.reshape((-1, 1, 2))], isClosed=True, color=color, thickness=thickness)

        # draw label if present
        label = r.get("label")
        if label:
            tx, ty = poly_px[0]
            cv2.putText(img, str(label), (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)


# ---------------------------
# Main demo
# ---------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--webcam", type=int, default=1,
                        help="Webcam device index (default=1). Use --webcam -1 to disable camera.")
    parser.add_argument("--live", action="store_true", help="Enable live detection from webcam")
    args = parser.parse_args()

    # initialize context
    context = {}
    rect.init_context(context)

    # add demo rectangles if not in live mode
    if not args.live:
        rect.add(context, [(0.1, 0.1), (0.3, 0.1), (0.3, 0.3), (0.1, 0.3)], timeout=5.0, label="A")
        rect.add(context, [(0.35, 0.2), (0.5, 0.2), (0.5, 0.4), (0.35, 0.4)], timeout=8.0, label="B")
        rect.add(context, [(0.7, 0.1), (0.85, 0.1), (0.85, 0.3), (0.7, 0.3)], timeout=3.0, label="C")

    # open camera if requested (device < 0 disables)
    cap = None
    if args.webcam is not None and args.webcam >= 0:
        cap = cv2.VideoCapture(args.webcam)
        if not cap.isOpened():
            print(f"Cannot open webcam {args.webcam}")
            return

    window_name = "Rect Demo"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    last_update = time.time()

    while True:
        if cap:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame from webcam")
                break
        else:
            frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)

        now = time.time()

        # 1) Expire old rectangles BEFORE merging new ones (fix ghost rectangles)
        rect.update_context(context)

        # 2) If live, detect and merge/add only matching rectangles
        if args.live and cap:
            detected = detect_from_frame(frame)
            for i, poly in enumerate(detected):
                # merge_or_add handles refreshing timestamp of existing rects
                label = f"L{int(time.time() * 1000) % 10000}"  # short unique-ish label
                rect.merge_or_add(context, poly, timeout=DETECT_TIMEOUT, label=label, epsilon=MERGE_EPSILON)

        # 3) Draw rectangles (skips degenerate ones)
        draw_rectangles(frame, context)

        # 4) show
        cv2.imshow(window_name, frame)

        # 5) keys: q or ESC quit; t touches first rectangle
        key = cv2.waitKey(50) & 0xFF
        if key == ord('q') or key == 27:
            break
        if key == ord('t') and context.get("rectangles"):
            rect.mark_touched(context, 0)

    if cap:
        cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
