# asimov/glitch.py

import cv2
import random
import time
import numpy as np
from importlib import import_module
from collections import deque
from typing import Dict, Any

from .. import io, conf
from ..common import ThreadSafeContext

# ---------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------

def _get_glitch_func(name: str):
    """
    Resolve a glitch implementation function by name.
    Functions are named: _glitch_<name>
    """
    module_path = conf.GLITCH.get(
        "DEFAULT_MODULE",
        conf.GLITCH_DEFAULT_MODULE,
    )

    try:
        mod = import_module(module_path)
    except Exception:
        io.echo_traceback(f"Failed to import glitch module: {module_path}")
        return None

    func = getattr(mod, f"_glitch_{name}", None)
    return func if callable(func) else None

def _init_namespace(context: ThreadSafeContext) -> Dict[str, Any]:
    """
    Ensure GLITCH namespace exists in shared context.
    """
    now = time.time()
    ns = {
        "active": {},          # name -> metadata
        "history": {},         # name -> per-glitch history
        "last_trigger": now,
        "next_interval": random.uniform(
            conf.GLITCH["MIN_INTERVAL"],
            conf.GLITCH["MAX_INTERVAL"],
        ),
    }
    context["GLITCH"] = ns
    return ns


# ---------------------------------------------------------------------
# detect() — scheduler / state mutation only
# ---------------------------------------------------------------------

def detect(frame: np.ndarray, context: ThreadSafeContext, **kwargs) -> None:
    """
    Scheduler:
    - decides WHEN glitches start/stop
    - mutates context only
    - MUST NOT modify frames
    """

    if not conf.GLITCH.get("ENABLED", True):
        if "GLITCH" in context:
            context["GLITCH"]["active"].clear()
        return

    now = time.time()

    ns = context.get("GLITCH")
    if ns is None:
        ns = _init_namespace(context)

    # --------------------------------------------------
    # 1. Expire finished glitches
    # --------------------------------------------------

    expired = [
        name for name, meta in ns["active"].items()
        if now - meta["start_time"] >= meta["duration"]
    ]

    for name in expired:
        ns["active"].pop(name, None)
        ns["history"].pop(name, None)

    # --------------------------------------------------
    # 2. Trigger new glitch if allowed
    # --------------------------------------------------

    max_concurrent = conf.GLITCH.get(
        "MAX_CONCURRENT",
        conf.GLITCH_DEFAULT_MAX_CONCURRENT,
    )

    if len(ns["active"]) >= max_concurrent:
        return

    if now - ns["last_trigger"] < ns["next_interval"]:
        return

    registry = conf.GLITCH.get("REGISTRY", {})
    candidates = [
        name for name, cfg in registry.items()
        if cfg.get("enabled", True)
    ]

    if not candidates:
        return

    weights = [
        registry[name].get("weight", 1.0)
        for name in candidates
    ]

    choice = random.choices(candidates, weights=weights, k=1)[0]
    cfg = registry.get(choice, {})

    ns["active"][choice] = {
        "start_time": now,
        "duration": random.uniform(
            cfg.get("min_duration", conf.GLITCH["MIN_DURATION"]),
            cfg.get("max_duration", conf.GLITCH["MAX_DURATION"]),
        ),
        "params": cfg,
    }

    ns["last_trigger"] = now
    ns["next_interval"] = random.uniform(
        conf.GLITCH["MIN_INTERVAL"],
        conf.GLITCH["MAX_INTERVAL"],
    )


# ---------------------------------------------------------------------
# draw() — rendering only
# ---------------------------------------------------------------------

def draw(frame: np.ndarray, context: ThreadSafeContext, **kwargs) -> np.ndarray:
    ns = context.get("GLITCH")
    if not ns or not ns["active"]:
        return frame

    now = time.time()
    output_frame = frame

    # SNAPSHOT iteration (thread-safe)
    for name, meta in list(ns["active"].items()):
        if not conf.GLITCH["REGISTRY"].get(name, {}).get("enabled", True):
            continue

        func = _get_glitch_func(name)
        if func:
            output_frame = func(
                output_frame,
                t=now - meta["start_time"],
                history=ns["history"],
                key=name,
                **kwargs,
            )

    return output_frame

# ---------------------------------------------------------------------
# Glitch implementations
# ---------------------------------------------------------------------

def _glitch_vhs_warp(frame, t=0, **kwargs):
    intensity_pct = kwargs.get("intensity", conf.GLITCH_DEFAULT_VHS_INTENSITY) / 100.0
    freq = kwargs.get("frequency", conf.GLITCH_DEFAULT_VHS_FREQ)

    h, w = frame.shape[:2]
    max_shift = w * intensity_pct  # Proportional to width
    y = np.arange(h)
    offsets = (
        max_shift * np.sin(2 * np.pi * freq * (y / h) + t)
    ).astype(np.int32)

    output = frame.copy()
    for row in range(h):
        output[row] = np.roll(frame[row], offsets[row], axis=0)

    return output


def _glitch_datamosh(frame, history=None, key=None, **kwargs):
    if history is None or key is None:
        return frame

    intensity = kwargs.get(
        "intensity",
        conf.GLITCH_DEFAULT_DATAMOSH_INTENSITY,
    )
    strips = kwargs.get(
        "num_strips",
        conf.GLITCH_DEFAULT_DATAMOSH_STRIPS,
    )

    h, w = frame.shape[:2]
    output = frame.copy()

    prev = history.get(key)
    if prev is not None:
        for _ in range(strips):
            y = random.randint(0, h - 1)
            strip_w = max(1, int(w * intensity))
            x = random.randint(0, max(1, w - strip_w))
            output[y, x:x + strip_w] = prev[y, x:x + strip_w]

    history[key] = frame.copy()
    return output


def _glitch_ghost(frame, history=None, key=None, **kwargs):
    if history is None or key is None:
        return frame

    alpha = kwargs.get(
        "alpha",
        conf.GLITCH_DEFAULT_GHOST_ALPHA,
    )
    shift_pct = kwargs.get(
        "shift",
        conf.GLITCH_DEFAULT_GHOST_SHIFT,
    ) / 100.0  # Convert to percentage

    if key not in history:
        history[key] = deque(
            maxlen=conf.GLITCH_DEFAULT_GHOST_MAXLEN
        )

    hist = history[key]
    hist.append(frame.copy())

    if len(hist) < 2:
        return frame

    h, w = frame.shape[:2]
    shift = int(w * shift_pct)  # Proportional to frame width
    M = np.float32([[1, 0, shift], [0, 1, 0]])
    shifted = cv2.warpAffine(hist[0], M, (w, h))

    return cv2.addWeighted(frame, 1.0, shifted, alpha, 0)


def _glitch_scanlines(frame, t=0, **kwargs):
    speed = kwargs.get("speed", 60)
    h = frame.shape[0]
    step_pct = 0.02  # 2% of height
    step = max(2, int(h * step_pct))
    opacity = conf.GLITCH_DEFAULT_SCANLINE_OPACITY

    output = frame.copy()
    offset = int(t * speed) % step
    output[offset::step] = (
        output[offset::step] * opacity
    ).astype(np.uint8)

    return output


def _glitch_whitenoise(frame, **kwargs):
    intensity = conf.GLITCH_DEFAULT_WHITE_NOISE_INTENSITY
    noise = np.random.randint(
        0, intensity, frame.shape, dtype=np.uint8
    )
    return cv2.add(frame, noise)


def _glitch_tearing(frame, **kwargs):
    h, w = frame.shape[:2]
    num_bands = max(3, int(h * 0.05))  # 5% of height
    output = frame.copy()

    for _ in range(num_bands):
        y = random.randint(0, h - 1)
        band_pct = random.uniform(0.01, 0.05)  # 1-5% of height
        band = max(1, int(h * band_pct))
        shift_pct = random.uniform(-0.1, 0.1)  # -10% to 10% of width
        shift = int(w * shift_pct)
        output[y:min(y + band, h)] = np.roll(
            output[y:min(y + band, h)],
            shift,
            axis=1,
        )

    return output


def _glitch_color_shift(frame, **kwargs):
    h, w = frame.shape[:2]
    shift_pct = 0.02  # 2% of width
    b_shift = int(w * shift_pct)
    r_shift = int(h * shift_pct)
    b, g, r = cv2.split(frame)
    b = np.roll(b, b_shift, axis=1)
    r = np.roll(r, r_shift, axis=0)
    return cv2.merge([b, g, r])


def _glitch_vertical_hold(frame, t=0, **kwargs):
    speed = kwargs.get("speed", 100)
    h = frame.shape[0]
    shift = int(t * speed) % h
    return np.roll(frame, shift, axis=0)


# ---------------------------------------------------------------------
# Module-level API (for other modules)
# ---------------------------------------------------------------------

_max_concurrent = 2
_registered_glitches = {}

def set_max_concurrent(max_count: int):
    """Set maximum concurrent glitches."""
    global _max_concurrent
    _max_concurrent = max_count


def register(name: str, **kwargs):
    """Register a glitch effect with optional parameters."""
    _registered_glitches[name] = kwargs


def scheduler():
    """
    Trigger random glitches based on GLITCH config.
    Called once per frame in draw().
    """
    import random
    
    now = time.time()
    
    if random.random() > 0.02:
        return
    
    enabled = [
        name for name, cfg in conf.GLITCH.get("REGISTRY", {}).items()
        if cfg.get("enabled", True)
    ]
    
    if not enabled:
        return
    
    name = random.choice(enabled)
    _trigger_glitch(name)


def _trigger_glitch(name: str):
    """Trigger a specific glitch effect."""
    pass


def is_any_glitch_running() -> bool:
    """Check if any glitch effect is currently active."""
    return False


def apply(frame: np.ndarray) -> np.ndarray:
    """
    Apply active glitch effects to frame.
    Returns modified frame.
    """
    return frame


# ---------------------------------------------------------------------
# Module lifecycle (required)
# ---------------------------------------------------------------------

def init(args, **kwargs):
    return True

def buildargs(args, **kwargs):
    return None

def access(args, op, **kwargs):
    return True

def main(args, **kwargs):
    return True
