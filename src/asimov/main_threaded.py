# asimov/main_threaded.py

import cv2
import threading
import time
import importlib
from . import io
from . import conf
from .common import ThreadSafeContext

_config_lock = threading.Lock()


def get_active_modules():
    """Dynamically loads modules defined in the OVERLAYS table."""
    active = []
    items = conf.get_overlays_items()

    for name, cfg in items:
        try:
            mod = importlib.import_module(cfg["module"])
            active.append({"name": name, "module": mod, "config": cfg})
        except ImportError as e:
            io.echo(f"Failed to load {name}: {e}", level="error")
    return active


def processing_thread(context: ThreadSafeContext, modules):
    """The unified background worker for all detections."""
    if conf.get_overlays_changed_event().is_set():
        conf.clear_overlays_changed()

    cap = cv2.VideoCapture(0)

    while True:
        if conf.get_overlays_changed_event().is_set():
            conf.clear_overlays_changed()

        success, frame = cap.read()
        if not success:
            break

        with context:
            for item in modules:
                if item["config"].get("enabled", True):
                    mod = item["module"]
                    if hasattr(mod, "detect"):
                        mod.detect(frame, context)

        time.sleep(0.01)
    cap.release()


def main():
    context = ThreadSafeContext()
    modules = get_active_modules()

    io.echo(f"Engine started with: {[m['name'] for m in modules]}")

    # Start detection worker
    t = threading.Thread(target=processing_thread, args=(context, modules), daemon=True)
    t.start()

    # Rendering Loop
    cap = cv2.VideoCapture(0)
    while True:
        success, frame = cap.read()
        if not success:
            break

        # 1. Input Handling (Generic Hotkey Logic)
        key_pressed = cv2.waitKey(1) & 0xFF
        if key_pressed != 255:
            char = chr(key_pressed).lower()
            if char == "q":
                break

            # Match character to hotkeys in the table
            for item in modules:
                if item["config"].get("hotkey") == char:
                    with _config_lock:
                        item["config"]["enabled"] = not item["config"]["enabled"]
                    status = "ON" if item["config"]["enabled"] else "OFF"
                    io.echo(f"TOGGLE: {item['name']} is now {status}")

        # 2. Rendering Phase
        with context:
            for item in modules:
                # Only draw if the module is enabled
                if item["config"].get("enabled", True):
                    mod = item["module"]
                    if hasattr(mod, "draw"):
                        frame = mod.draw(frame, context)

        cv2.imshow("Asimov Main Threaded", frame)

    cap.release()
    cv2.destroyAllWindows()
