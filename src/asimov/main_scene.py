# asimov/main_scene.py

import sys
import threading
import time
import cv2
import numpy as np
import pyvirtualcam

from . import io
from . import module, common
from .common import ThreadSafeContext

# ------------------------------------------------------------
# Shared state
# ------------------------------------------------------------

context = ThreadSafeContext()
logic_lock = threading.Lock()
stop_event = threading.Event()

# ------------------------------------------------------------
# Signature stubs (validation)
# ------------------------------------------------------------


def _stub_detect(frame: np.ndarray, context: ThreadSafeContext, **kwargs):
    pass


def _stub_draw(frame: np.ndarray, context: ThreadSafeContext, **kwargs) -> np.ndarray:
    pass


# ------------------------------------------------------------
# Logic thread (detect only)
# ------------------------------------------------------------


def _logic_thread(modules):
    try:
        while not stop_event.is_set():
            with logic_lock:
                frame = context.get("SHARED_FRAME")

            if frame is not None:
                for m in modules:
                    if not m["enabled"] or not m["can_detect"]:
                        continue
                    try:
                        m["ref"].detect(frame, context)
                    except Exception:
                        io.echo_traceback(f"detect() crash in module '{m['name']}'")

            time.sleep(0.01)

    except Exception:
        io.echo_traceback("CRITICAL: logic thread died")


# ------------------------------------------------------------
# Scene resolution
# ------------------------------------------------------------


def _resolve_scene_modules(args, scn):
    resolved = []

    for entry in sorted(scn["modules"], key=lambda x: x.get("order", 99)):
        try:
            mod = module.get(entry["module"], args)
        except Exception:
            io.echo_traceback(f"Failed loading module '{entry['name']}'")
            continue

        # lifecycle (ONCE)
        if module.run(args, mod, context=context, argv=sys.argv) is False:
            io.echo(f"Module '{entry['name']}' rejected during init", level="error")
            continue

        resolved.append(
            {
                "name": entry["name"],
                "ref": mod,
                "enabled": entry.get("enabled", True),
                "hotkey": entry.get("hotkey"),
                "can_detect": module.validate_function(
                    mod, "detect", _stub_detect, silent=True
                ),
                "can_draw": module.validate_function(
                    mod, "draw", _stub_draw, silent=True
                ),
                "conf": entry.get("conf", {}),
            }
        )

    return resolved


# ------------------------------------------------------------
# Input helpers
# ------------------------------------------------------------


def _handle_hotkey(key, modules):
    ch = chr(key).lower()
    for m in modules:
        if m["hotkey"] == ch:
            m["enabled"] = not m["enabled"]
            io.echo(f"TOGGLE: {m['name']} → {m['enabled']}", level="info")


# ------------------------------------------------------------
# Module API (required)
# ------------------------------------------------------------


def init(args, **kwargs):
    return True


def access(args, op, /, **kwargs):
    return op == "run"


def buildargs(args=None, **kwargs):
    return None


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------


def main(args, **kwargs):
    """
    Scene-driven producer / consumer pipeline.
    """

    # --------------------------------------------------------
    # Load scene
    # --------------------------------------------------------

    scn = scene.load(args)
    io.echo(f"Loaded scene '{scn['name']}' ({len(scn['modules'])} modules)", level="ok")

    modules = _resolve_scene_modules(args, scn)

    # --------------------------------------------------------
    # Camera setup
    # --------------------------------------------------------

    cap = cv2.VideoCapture(args.capture_device)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.capture_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.capture_height)
    cap.set(cv2.CAP_PROP_FPS, args.capture_fps)

    if not common.camera_ready(cap):
        io.echo("Camera failed to initialize", level="error")
        return False

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 1

    # --------------------------------------------------------
    # Start logic thread
    # --------------------------------------------------------

    t = threading.Thread(target=_logic_thread, args=(modules,), daemon=True)
    t.start()

    # --------------------------------------------------------
    # Render loop
    # --------------------------------------------------------

    try:
        with pyvirtualcam.Camera(width=width, height=height, fps=fps) as vcam:
            io.echo(f"VirtualCam {width}x{height} @{fps}", level="ok")

            while True:
                ok, raw = cap.read()
                if not ok:
                    break

                frame = raw.copy()

                with logic_lock:
                    context["SHARED_FRAME"] = frame

                key = cv2.waitKey(1)
                if key == 27:
                    with logic_lock:
                        stop_event.set()
                    break
                if key > 0:
                    _handle_hotkey(key, modules)

                for m in modules:
                    if not m["enabled"] or not m["can_draw"]:
                        continue
                    try:
                        out = m["ref"].draw(frame, context)
                        if isinstance(out, np.ndarray):
                            frame = out
                    except Exception:
                        io.echo_traceback(f"draw() crash in module '{m['name']}'")

                vcam.send(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                vcam.sleep_until_next_frame()
                cv2.imshow("Asimov", frame)

    finally:
        with logic_lock:
            context["SHARED_FRAME"] = None
            stop_event.set()
        t.join(timeout=2.0)
        cap.release()
        cv2.destroyAllWindows()

    return True
