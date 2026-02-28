import os
import time
import math
import threading

from typing import Optional, Union

import cv2

from . import conf


def safe_path(
    *components: Union[str, os.PathLike],
    base_dir: Optional[Union[str, os.PathLike]] = None,
    must_exist: bool = False,
    resolve_symlinks: bool = True,
) -> str:
    """
    Construct a robust, secure, and flexible filesystem path.

    Expands user (~) and environment variables, normalizes, makes the path absolute,
    and (optionally) ensures it stays within a specified base directory (security check).

    Parameters
    ----------
    *components : str | os.PathLike
        Path components to join, e.g. ("~/data", "images", "foo.png").
    base_dir : str | os.PathLike | None
        Optional. If given, ensures the resulting path is inside this directory
        and validates that the base_dir exists and is a directory.
    must_exist : bool
        If True, raises FileNotFoundError if the final path does not exist.
    resolve_symlinks : bool
        If True, resolves symbolic links before applying traversal checks.

    Returns
    -------
    str
        The fully resolved, absolute, normalized safe path.

    Raises
    ------
    ValueError
        If directory traversal, path escape outside base_dir is detected, or base_dir doesn't exist.
    FileNotFoundError
        If must_exist=True and the path does not exist.
    """

    if not components:
        raise ValueError("At least one path component must be provided.")

    # 1. Expand ~ and environment variables
    expanded = [os.path.expandvars(os.path.expanduser(str(c))) for c in components]

    # 2. Join, normalize, and make absolute
    joined_path = os.path.normpath(os.path.join(*expanded))
    abs_path = os.path.abspath(joined_path)

    # 3. Optionally resolve symlinks for maximum safety
    # os.path.realpath is preferred for security as it resolves all symlinks
    resolved_path = os.path.realpath(abs_path) if resolve_symlinks else abs_path

    # 4. Traversal/Containment Check (The security feature)
    if base_dir is not None:
        base_dir_expanded = os.path.expandvars(os.path.expanduser(str(base_dir)))
        base_dir_abs = os.path.abspath(base_dir_expanded)
        base_dir_resolved = (
            os.path.realpath(base_dir_abs) if resolve_symlinks else base_dir_abs
        )

        # Security Check 1: Base directory must exist and be a directory
        if not os.path.isdir(base_dir_resolved):
            raise ValueError(
                f"Invalid base_dir: Base directory must exist and be a directory: {base_dir_resolved}"
            )

        # Security Check 2: Check for path escape (directory traversal)
        # Ensure resolved_path starts with base_dir_resolved plus the separator
        # OR is exactly the base_dir_resolved path (if the target IS the base dir).
        is_contained = (
            resolved_path.startswith(base_dir_resolved + os.sep)
            or resolved_path == base_dir_resolved
        )

        if not is_contained:
            raise ValueError(
                f"Invalid path: {resolved_path} is outside allowed base_dir {base_dir_resolved}"
            )

    # 5. Existence Check
    if must_exist and not os.path.exists(resolved_path):
        raise FileNotFoundError(f"Path not found: {resolved_path}")

    return resolved_path


get_safe_path = safe_path


def safe_distance(p1, p2):
    """
    Compute Euclidean distance between two points.

    Supports:
    - 2D points (x, y)
    - 3D points (x, y, z)
    - Input as tuple, list, or numpy array

    Returns:
        float: Euclidean distance

    Raises:
        ValueError: if points are invalid or have mismatched dimensions
    """
    # Convert to list/tuple if NumPy array
    try:
        p1 = tuple(p1)
        p2 = tuple(p2)
    except TypeError:
        raise ValueError(
            f"safe_distance: Points must be iterable, got {type(p1)} and {type(p2)}"
        )

    if len(p1) != len(p2):
        raise ValueError(
            f"safe_distance: Points must have same dimensions, got {len(p1)} and {len(p2)}"
        )

    # Compute Euclidean distance
    squared_diff_sum = sum((a - b) ** 2 for a, b in zip(p1, p2))
    return math.sqrt(squared_diff_sum)


# ---------
# logging
# ---------
import logging
import logging.handlers

# default syslog handler
default_handler = logging.handlers.SysLogHandler(address="/dev/log")
default_formatter = logging.Formatter(
    "%(name)s[%(process)d]: %(levelname)s %(message)s"
)
default_handler.setFormatter(default_formatter)


def logentry(
    message,
    level=logging.INFO,
    *,
    handler=None,
    formatter=None,
    logger_name=conf.LOGGER_NAME,
):
    """
    Write a log entry to syslog (by default), with optional handler/formatter overrides.

    Args:
        message (str): The log message.
        level (int): Logging level (default=logging.INFO).
        handler (logging.Handler, optional): Custom logging handler.
        formatter (logging.Formatter, optional): Custom formatter.
        logger_name (str): Name for the logger (default="myapp").
    """

    h = handler or default_handler
    f = formatter or default_formatter

    # Ensure formatter is applied
    h.setFormatter(f)

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)  # capture all levels
    if not any(isinstance(x, type(h)) for x in logger.handlers):
        logger.addHandler(h)

    levels = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warn": logging.WARNING,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
        "crit": logging.CRITICAL,
        #        "exception":logging.EXCEPTION,
    }

    if level in levels:
        level = levels[level]
    else:
        level = logging.INFO

    logger.log(level, message)
    return


class CameraCapture(threading.Thread):
    def __init__(self, source):
        super().__init__(name="CameraCaptureThread")
        self.source = source
        self.frame = None
        self.stopped = False
        self.lock = threading.Lock()
        self._stop_event = threading.Event()
        self.thread = None
        self.actual_width = 0
        self.actual_height = 0
        self.actual_fps = 0

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        # Wait for hardware to warm up so Main has dimensions
        timeout = time.time() + 7.0
        while self.frame is None and time.time() < timeout:
            time.sleep(0.1)
        if self.frame is None:
            raise RuntimeError("Webcam failed to initialize.")
        return self

    def _run(self):
        """Background thread: Opens, Reads, and Closes the camera."""
        from . import cap, io

        self.cap, error = cap.open_ready(self.source)
        if self.cap is None:
            io.echo(f"{{error}}CameraCapture: Hardware not available: {error}{{/all}}")
            self.stopped = True
            return

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, conf.CAP_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, conf.CAP_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, conf.CAP_FPS)

        self.actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.actual_fps = self.cap.get(cv2.CAP_PROP_FPS)

        try:
            while not self._stop_event.is_set():
                ret, frame = self.cap.read()

                if not ret:
                    time.sleep(0.1)
                    continue

                flipped = cv2.flip(frame, 1)
                with self.lock:
                    self.frame = flipped
        except Exception as e:
            logentry(f"CameraCapture: _run: exception {e}", level="error")
        finally:
            self._cleanup()

    def read(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def stop(self):
        self._stop_event.set()
        io.echo("CameraCapture: stop event")

    def _cleanup(self):
        """Releases the camera and logs the shutdown."""
        if self.cap and self.cap.isOpened():
            self.cap.release()
        logentry("CameraCapture: Resources released and thread exiting.")


class ThreadSafeContext(dict):
    """
    A dictionary subclass that uses a threading lock for all access.
    Maintains backward compatibility with existing detection and drawing functions.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock = threading.Lock()
        self._stats = {
            "capture_fps": 0.0,
            "processing_fps": 0.0,
            "render_fps": 0.0,
            "avg_fps": 0.0,
        }

    def set_stat(self, key, value):
        with self._lock:
            self._stats[key] = value
            # Recalculate average whenever a component updates
            self._stats["avg_fps"] = (
                sum(
                    [
                        self._stats["capture_fps"],
                        self._stats["processing_fps"],
                        self._stats["render_fps"],
                    ]
                )
                / 3.0
            )

    def get_stats(self):
        with self._lock:
            return self._stats.copy()

    def __getitem__(self, key):
        with self._lock:
            return super().__getitem__(key)

    def __setitem__(self, key, value):
        with self._lock:
            super().__setitem__(key, value)

    def __delitem__(self, key):
        with self._lock:
            super().__delitem__(key)

    def __contains__(self, key):
        with self._lock:
            return super().__contains__(key)

    def get(self, key, default=None):
        with self._lock:
            return super().get(key, default)

    def copy(self):
        """Returns a non-thread-safe snapshot for rendering."""
        with self._lock:
            return super().copy()


class OneEuroFilter:
    """
    One Euro Filter: https://cristal.univ-lille.fr/~casiez/1euro/
    Keeps smooth values but reacts faster to quick movements.
    """

    def __init__(self, freq=30, min_cutoff=1.0, beta=0.01, dcutoff=1.0, init=None):
        self.freq = freq  # Hz, frame rate estimate
        self.min_cutoff = min_cutoff  # baseline smoothing
        self.beta = beta  # speed sensitivity
        self.dcutoff = dcutoff  # derivative smoothing
        self.last_time = None
        self.x_prev = init
        self.dx_prev = 0

    def _alpha(self, cutoff, dt):
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def update(self, x):
        now = time.time()
        if self.last_time is None:
            dt = 1.0 / self.freq
        else:
            dt = max(now - self.last_time, 1e-6)
        self.last_time = now

        if self.x_prev is None:
            self.x_prev = x
            self.dx_prev = 0

        # derivative
        dx = (x - self.x_prev) / dt
        a_d = self._alpha(self.dcutoff, dt)
        dx_hat = a_d * dx + (1 - a_d) * self.dx_prev

        # adaptive cutoff
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self._alpha(cutoff, dt)

        # filtered value
        x_hat = a * x + (1 - a) * self.x_prev

        self.x_prev = x_hat
        self.dx_prev = dx_hat
        return x_hat
