# cap.py - Camera capture utilities

import os
import subprocess
import sys
import time
import cv2

from .common import safe_path


def list_devices():
    """List available video capture devices.

    Returns:
        List of device indices that can be opened
    """
    devices = []
    for i in range(16):
        try:
            code = f"import cv2; vc = cv2.VideoCapture({i}, cv2.CAP_V4L2); print('OK' if vc.isOpened() else 'FAIL', flush=True)"
            result = subprocess.run(
                [sys.executable, "-c", code], capture_output=True, timeout=1
            )
            if b"OK" in result.stdout:
                devices.append(i)
        except Exception:
            pass
    return devices


def device_exists(device):
    """Check if a device exists and can be opened.

    Args:
        device: Device index (int) or path (str)

    Returns:
        True if device can be opened, False otherwise
    """
    if isinstance(device, str):
        return os.path.exists(device)

    # For numeric indices, check if in list of available devices
    available = list_devices()
    return device in available


def open(device, timeout=2):
    """Open camera with timeout to avoid hanging on invalid/unavailable devices.

    Args:
        device: Device index (int) or path (str)
        timeout: Maximum seconds to wait for camera to open

    Returns:
        cv2.VideoCapture object if successful, None if timeout/failed
        error message string if failed, None if successful
    """
    # Convert string devices using safe_path
    if isinstance(device, str):
        device = safe_path(device)

    # Check if device exists first
    if isinstance(device, int) and not device_exists(device):
        available = list_devices()
        return None, f"Device {device} not found. Available: {available}"

    if isinstance(device, str) and not os.path.exists(device):
        return None, f"Device file {device} not found"

    try:
        # Try V4L2 backend first - it's more reliable on Linux
        code = f"""
import cv2
vc = cv2.VideoCapture({device}, cv2.CAP_V4L2)
if vc.isOpened():
    print('OK', flush=True)
else:
    print('FAIL', flush=True)
"""
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, timeout=timeout
        )
        stdout = result.stdout.decode() if result.stdout else ""
        stderr = result.stderr.decode() if result.stderr else ""

        if "OK" in stdout:
            return cv2.VideoCapture(device, cv2.CAP_V4L2), None

        # Parse error from stderr
        error_msg = _parse_cv_error(stderr)
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
