# cap.py - Camera capture utilities

import subprocess
import sys
import time
import cv2


def open(device, timeout=5):
    """Open camera with timeout to avoid hanging on invalid/unavailable devices.

    Args:
        device: Camera device index (int) or path (str)
        timeout: Maximum seconds to wait for camera to open

    Returns:
        cv2.VideoCapture object if successful, None if timeout/failed
        error message string if failed, None if successful
    """
    try:
        code = f"""
import cv2
import sys
vc = cv2.VideoCapture({device})
if vc.isOpened():
    ret, frame = vc.read()
    if ret and frame is not None:
        print('OK', flush=True)
    else:
        print('NO_FRAME', flush=True)
else:
    print('FAIL', flush=True)
"""
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, timeout=timeout
        )
        stdout = result.stdout.decode() if result.stdout else ""
        stderr = result.stderr.decode() if result.stderr else ""

        if "OK" in stdout:
            return cv2.VideoCapture(device), None

        # Parse error from stderr
        error_msg = _parse_cv_error(stderr)
        if "NO_FRAME" in stdout:
            error_msg = "Camera opened but returned no frame"
        return None, error_msg
    except subprocess.TimeoutExpired:
        return None, "Timeout waiting for camera"
    except Exception as e:
        return None, str(e)


def _parse_cv_error(stderr):
    """Parse OpenCV error message to extract useful info."""
    if not stderr:
        return "Unknown error"
    if "index out of range" in stderr:
        return "Camera index out of range"
    if "can't open camera" in stderr:
        return "Cannot open camera"
    if "No such file" in stderr:
        return "Device file not found"
    if "Permission denied" in stderr:
        return "Permission denied"
    # Return first line of error
    lines = stderr.strip().split("\n")
    return lines[0] if lines else "Unknown error"


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


def release(cap):
    """Safely release a camera handle.

    Args:
        cap: cv2.VideoCapture object or None

    Returns:
        True if released successfully, False otherwise
    """
    if cap is None:
        return False
    try:
        cap.release()
        return True
    except Exception:
        return False
