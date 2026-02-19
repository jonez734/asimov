# asimov/main_generic.py

import sys
import argparse
import cv2
import threading
import time
import numpy as np
import pyvirtualcam
from . import io, conf, module, common
from .common import ThreadSafeContext

# Initialize shared context and global lock
context = ThreadSafeContext()
logic_lock = threading.Lock()

# --- 1. Signature Callables for Validation ---

def _stub_ui_schema(context: ThreadSafeContext, /, **kwargs) -> dict:
    pass

def _stub_detect(frame: np.ndarray, context: ThreadSafeContext, **kwargs):
    """Template for detect() signature validation."""
    pass

def _stub_draw(frame: np.ndarray, context: ThreadSafeContext, **kwargs) -> np.ndarray:
    """Template for draw() signature validation."""
    pass

# --- 2. Thread Logic ---

def _consumer(modules: list, args: argparse.Namespace):
    """
    LOGIC THREAD: Background worker for heavy math.
    Executes detect() on already-resolved modules.
    """
    try:
        while True:
            # LOCK: Protected read from shared context
            with logic_lock:
                frame = context.get("SHARED_FRAME")

            if frame is not None:
                for item in modules:
                    if not item.get("config", {}).get("enabled", True):
                        continue

                    try:
                        m = item["module_ref"]

                        # Signature validation before execution
                        if module.check_func(m, "detect", _stub_detect):
                            with logic_lock:
                                m.detect(frame, context)

                    except Exception:
                        io.echo_traceback(
                            f"Logic Thread Error in module: {item['name']}"
                        )

            time.sleep(0.01)

    except Exception:
        io.echo_traceback("CRITICAL: Consumer thread collapsed")

# --- 3. Helper Functions ---

def get_active_modules(args):
    active = []
    overlays = getattr(conf, "OVERLAYS", {})
    items = sorted(overlays.items(), key=lambda x: x[1].get("order", 99))

    for name, cfg in items:
        mod_path = cfg["module_path"]
        try:
            mod = module.get(mod_path)
        except Exception:
            io.echo_traceback(f"Module rejected (exception at load): {name}")
            raise

        try:
            if module.check(args, mod, op="run", silent=False) is False:
                io.echo(f"get_active_modules.100: module.check() returned False")
                continue
        except Exception:
            io.echo_traceback(f"Module rejected: {name}")
            continue

        active.append({
            "name": name,
            "module_path": mod_path,
            "module_ref": mod,
            "config": cfg,
        })

    return active

def handle_hotkeys(key, modules):
    """Toggles module state based on hotkeys in conf.py."""
    char = chr(key).lower()
    for item in modules:
        if item.get("config", {}).get("hotkey") == char:
            item["config"]["enabled"] = not item["config"]["enabled"]
            # Using new echo levels from echo.py
            io.echo(f"TOGGLE: {item['name']} is now {item['config']['enabled']}", level="info")

# --- 4. Module Lifecycle ---

def init(args, **kwargs): return True
def access(args, op="run", **kwargs): return op == "run"
def buildargs(args=None, **kwargs): return None 

def main(args, **kwargs):
    """
    Main Thread: Producer/Renderer loop.
    Lifecycle is executed ONCE per module.
    Per-frame work is detect()/draw() only.
    """

    # -------------------------------------------------
    # 1. Resolve and validate active modules (ONCE)
    # -------------------------------------------------
    modules = get_active_modules(args)
    io.echo(f"asimov.main_generic.main.100: loaded {len(modules)} modules", level="debug")

    # Run lifecycle once and cache capabilities
    for item in modules:
        mod = item["module_ref"]

        item["can_detect"] = False
        item["can_draw"] = False

        try:
            # Full lifecycle once
            if module.run(args, mod, context=context, argv=sys.argv) is False:
                io.echo(f"Module '{item['name']}' rejected during lifecycle", level="error")
                continue

            # Cache detect() validity
            if hasattr(mod, "detect"):
                item["can_detect"] = module.validate_function(
                    mod, "detect", _stub_detect
                )

            # Cache draw() validity
            if hasattr(mod, "draw"):
                item["can_draw"] = module.validate_function(
                    mod, "draw", _stub_draw
                )

            if hasattr(mod, "ui_schema"):
                item["has_ui_schema"] = module.validate_function(
                    mod, "ui_schema", _stub_ui_schema
                )

        except Exception:
            io.echo_traceback(f"Module '{item['name']}' failed during initialization")
            continue

    # -------------------------------------------------
    # 2. Initialize camera
    # -------------------------------------------------
    io.echo(f"attempting to open capture camera: {args.capture_device}")
    cap = cv2.VideoCapture(args.capture_device)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.capture_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.capture_height)
    cap.set(cv2.CAP_PROP_FPS, args.capture_fps)

    if not common.camera_ready(cap):
        io.echo("Camera hardware failed to initialize", level="error")
        cap.release()
        return False

    io.echo(f"cap opened and ready", level="debug")

    # Prime first frame
#    while True:
#        success, frame = cap.read()
#        if success and frame is not None:
#            break

    actual_width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps    = int(cap.get(cv2.CAP_PROP_FPS)) or 1

    # -------------------------------------------------
    # 3. Start logic thread (detect only, no validation)
    # -------------------------------------------------
    t = threading.Thread(
        target=_consumer,
        args=(modules, args),
        daemon=True
    )
    t.start()

    # -------------------------------------------------
    # 4. Render / output loop
    # -------------------------------------------------
    try:
        with pyvirtualcam.Camera(
            width=actual_width,
            height=actual_height,
            fps=actual_fps
        ) as vcam:

            io.echo(
                f"Virtual Camera Active: {actual_width}x{actual_height} @ {actual_fps}fps",
                level="ok"
            )

            while True:
                success, raw_frame = cap.read()
                if not success:
                    io.echo("Failed to grab frame from device", level="error")
                    break

                frame = raw_frame.copy()

                # Update shared frame for logic thread
                with logic_lock:
                    context["SHARED_FRAME"] = frame

                # Input handling
                key = cv2.waitKey(1)
                if key == 27:
                    break  # ESC
                if key > 0:
                    handle_hotkeys(key, modules)

                # Rendering phase (draw only)
                for item in modules:
                    if not item.get("config", {}).get("enabled", True):
                        continue

                    if not item.get("can_draw", False):
                        continue

                    try:
                        result = item["module_ref"].draw(frame, context)
                        if isinstance(result, np.ndarray):
                            frame = result
                    except Exception:
                        io.echo_traceback(
                            f"draw() failure in module '{item['name']}'"
                        )

                frame = cv2.flip(frame, 1)

                # Output
                vcam.send(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                vcam.sleep_until_next_frame()
                cv2.imshow(
                    getattr(conf, "WINDOW_NAME", "Asimov Preview"),
                    frame
                )

    except Exception:
        io.echo_traceback("Main lifecycle crash")

    finally:
        cap.release()
        cv2.destroyAllWindows()

    return True
