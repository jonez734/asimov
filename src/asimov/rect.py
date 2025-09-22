# asimov/rect.py

import cv2
import time
import numpy as np

__all__ = ["detect", "merge", "draw"]  # public functions

# Default timeout (seconds) and tolerance (fraction of size)
DEFAULT_RECT_TIMEOUT = 0.5
MERGE_TOLERANCE_RATIO = 0.2  # 20% of rectangle diagonal

_rectangles = []


def _centroid(polygon):
    """Return centroid (x, y) of a polygon."""
    M = cv2.moments(polygon)
    if M["m00"] == 0:
        return np.mean(polygon, axis=0)
    return (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))


def _rect_size(polygon):
    """Return approximate size (diagonal length) of bounding box."""
    x, y, w, h = cv2.boundingRect(polygon)
    return np.hypot(w, h)


def _is_duplicate(p1, p2):
    """Check if two polygons are duplicates based on centroid distance relative to their size."""
    c1, c2 = _centroid(p1), _centroid(p2)
    dist = np.linalg.norm(np.array(c1) - np.array(c2))

    # Use average diagonal of the two rectangles
    size = (_rect_size(p1) + _rect_size(p2)) / 2
    tolerance = size * MERGE_TOLERANCE_RATIO

    return dist < tolerance


def detect(frame):
    """Detect rectangles in a frame, timestamp them, merge duplicates with updates,
    and expire old ones."""
    global _rectangles
    now = time.time()
    detected = []

    # --- preprocess frame ---
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 1)
    canny = cv2.Canny(blur, 50, 150)
    contours, _ = cv2.findContours(canny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # --- detect new rectangles ---
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 1000:
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
            if len(approx) == 4:
                polygon = approx.reshape((4, 2))
                detected.append(polygon)

    # --- update existing rectangles or add new ones ---
    merge(detected)

    # --- remove expired rectangles ---
    now = time.time()
    _rectangles[:] = [r for r in _rectangles if now - r["timestamp"] <= r["timeout"]]

    return _rectangles


def merge(new_polygons):
    """Merge new polygons into existing rectangles, updating polygon and timestamp if duplicate."""
    global _rectangles
    now = time.time()

    for poly in new_polygons:
        merged = False
        for r in _rectangles:
            if _is_duplicate(poly, r["polygon"]):
                # update polygon and timestamp
                r["polygon"] = poly
                r["timestamp"] = now
                merged = True
                break
        if not merged:
            _rectangles.append({
                "polygon": poly,
                "timestamp": now,
                "timeout": DEFAULT_RECT_TIMEOUT,
            })


def draw(frame, rectangles=None, color=(0, 255, 0), thickness=2):
    """Draw rectangles on a frame. If rectangles is None, draw current tracked rectangles."""
    if rectangles is None:
        rectangles = _rectangles
    for r in rectangles:
        pts = r["polygon"].reshape((-1, 1, 2))
        cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=thickness)
    return frame
