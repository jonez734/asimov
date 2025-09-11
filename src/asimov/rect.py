import cv2
import time
import numpy as np

# Default timeout (seconds) and tolerance (fraction of size)
DEFAULT_RECT_TIMEOUT = 2.0
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
    """Check if two polygons are duplicates based on centroid distance
    relative to their size."""
    c1, c2 = _centroid(p1), _centroid(p2)
    dist = np.linalg.norm(np.array(c1) - np.array(c2))

    # Use average diagonal of the two rectangles
    size = (_rect_size(p1) + _rect_size(p2)) / 2
    tolerance = size * MERGE_TOLERANCE_RATIO

    return dist < tolerance


def detect_rectangles(frame):
    """Detect rectangles in a frame, timestamp them, merge duplicates with updates,
    and expire old ones unless touched."""
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
    for poly in detected:
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
                "touched": False,
            })

    # --- remove expired rectangles (unless touched) ---
    still_alive = []
    for r in _rectangles:
        if r["touched"]:
            r["timestamp"] = now  # keep it alive
            still_alive.append(r)
        elif now - r["timestamp"] <= r["timeout"]:
            still_alive.append(r)
    _rectangles = still_alive

    return _rectangles


def touch_rectangle(rect):
    """Mark a rectangle as touched (prevents expiration)."""
    rect["touched"] = True


def release_rectangle(rect):
    """Release a rectangle so it can expire normally again."""
    rect["touched"] = False
