# cap.py - Camera capture utilities

import threading
import time

import cv2


def open(device, timeout=2):
    """Open camera with timeout to avoid hanging on invalid/unavailable devices.

    Args:
        device: Camera device index (int) or path (str)
        timeout: Maximum seconds to wait for camera to open

    Returns:
        cv2.VideoCapture object if successful, None if timeout/failed
    """
    result = {"cap": None, "opened": False}

    def try_open():
        cap = cv2.VideoCapture(device)
        result["cap"] = cap
        if cap.isOpened():
            result["opened"] = True

    t = threading.Thread(target=try_open)
    t.daemon = True
    t.start()
    t.join(timeout)

    if t.is_alive():
        if result["cap"]:
            result["cap"].release()
        return None
    return result["cap"] if result["opened"] else None


def ready(cap, timeout=5):
    """Check if camera is ready by attempting to read a frame.

    Args:
        cap: cv2.VideoCapture object
        timeout: Maximum seconds to wait for a valid frame

    Returns:
        True if camera returns a valid frame, False on timeout
    """
    start_time = time.time()
    while True:
        ret, frame = cap.read()
        if ret and frame is not None:
            return True
        if time.time() - start_time >= timeout:
            return False
        time.sleep(0.10)


def configure(cap, width=None, height=None, fps=None):
    """Configure camera capture properties.

    Args:
        cap: cv2.VideoCapture object
        width: Desired frame width (None to skip)
        height: Desired frame height (None to skip)
        fps: Desired FPS (None to skip)

    Returns:
        Tuple (actual_width, actual_height, actual_fps) or None on failure
    """
    if width is not None:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    if height is not None:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if fps is not None:
        cap.set(cv2.CAP_PROP_FPS, fps)

    if not cap.isOpened():
        return None

    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = int(cap.get(cv2.CAP_PROP_FPS)) or 1

    return (actual_width, actual_height, actual_fps)
