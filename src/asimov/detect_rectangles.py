import cv2
import time
import numpy as np

MIN_AREA = 1000
DETECTION_INTERVAL = 2.5  # seconds

last_detection_time = 0

def rectangles_overlap(rect1, rect2, threshold=0.5):
    # rect: (x, y, w, h)
    x1, y1, w1, h1 = rect1
    x2, y2, w2, h2 = rect2

    # Calculate intersection
    xi1 = max(x1, x2)
    yi1 = max(y1, y2)
    xi2 = min(x1 + w1, x2 + w2)
    yi2 = min(y1 + h1, y2 + h2)
    inter_width = max(0, xi2 - xi1)
    inter_height = max(0, yi2 - yi1)
    intersection = inter_width * inter_height

    area1 = w1 * h1
    area2 = w2 * h2
    union = area1 + area2 - intersection

    if union == 0:
        return False

    iou = intersection / union
    return iou > threshold

def should_run(context):
    global last_detection_time
    now = time.monotonic()
    if now - last_detection_time >= DETECTION_INTERVAL:
        last_detection_time = now
        return True
    return False

def process(frame, context):
    h, w, _ = frame.shape

    # Existing rectangles and trackers
    rectangles = context.get("rectangles", [])
    tracker_id_counter = context.get("tracker_id_counter", 0)

    imgGray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    imgBlur = cv2.GaussianBlur(imgGray, (5, 5), 1)
    imgCanny = cv2.Canny(imgBlur, 50, 150)
    contours, _ = cv2.findContours(imgCanny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    new_detections = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < MIN_AREA:
            continue

        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4:
            x, y, rect_w, rect_h = cv2.boundingRect(approx)

            # Skip rectangles near edges
            if x <= 5 or y <= 5 or x + rect_w >= w - 5 or y + rect_h >= h - 5:
                continue

            # Check overlap with existing rectangles
            overlaps_existing = False
            for r in rectangles:
                if rectangles_overlap((x, y, rect_w, rect_h), r["bbox"]):
                    overlaps_existing = True
                    break
            if overlaps_existing:
                continue

            new_detections.append((x, y, rect_w, rect_h))

    # Add new detections as trackers and rectangles
    for bbox in new_detections:
        tracker = cv2.TrackerCSRT_create()
        tracker.init(frame, bbox)
        polygon = np.array([
            [bbox[0], bbox[1]],
            [bbox[0] + bbox[2], bbox[1]],
            [bbox[0] + bbox[2], bbox[1] + bbox[3]],
            [bbox[0], bbox[1] + bbox[3]]
        ], dtype=np.int32).reshape((-1, 1, 2))

        rectangles.append({
            "tracker": tracker,
            "id": tracker_id_counter,
            "bbox": bbox,
            "polygon": polygon,
            "touching": False
        })
        tracker_id_counter += 1

    # Save back to context
    context["rectangles"] = rectangles
    context["tracker_id_counter"] = tracker_id_counter

    return frame, context
