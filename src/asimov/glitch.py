import cv2
import random
import time
import importlib
from dataclasses import dataclass, field
from typing import Optional, Callable
import numpy as np

# === Global configuration (tweak here) ===
MIN_DURATION = 0.3        # seconds
MAX_DURATION = 1.0
MIN_INTERVAL = 8.0        # seconds between glitches
MAX_INTERVAL = 20.0

@dataclass
class Glitch:
    name: str
    enabled: bool = True
    running: bool = False
    start_time: Optional[float] = 0.0
    duration: Optional[float] = 0.0
    module: str = "asimov.glitch"   # module where the glitch function lives
    func: Optional[Callable] = field(default=None, repr=False)
    trigger_interval: float = 0.0
    kwargs: dict = field(default_factory=dict)

    def resolve_func(self):
        """Resolve the glitch function dynamically based on name + module."""
        if self.func is not None:
            return self.func
        mod = importlib.import_module(self.module)
        func_name = f"_glitch_{self.name}"
        self.func = getattr(mod, func_name, None)
        if self.func is None:
            raise ValueError(f"Glitch function {func_name} not found in {self.module}")
        return self.func

# Global state
_glitches: dict[str, Glitch] = {}
_sequential_mode: bool = False
_seq_index: int = 0
_module = importlib.import_module("asimov.glitch")

def register(name: str, module: str = "asimov.glitch", **kwargs):
    """Register a glitch by name (function resolved later)."""
    if not hasattr(_module, f"_glitch_{name}"):
        raise ValueError(f"Glitch function _{name} not found in asimov.glitch")
    
    g = Glitch(name=name, kwargs=kwargs)

    # assign an initial cooldown so glitches don’t all start at once
    g.start_time = time.time()
    g.trigger_interval = random.uniform(MIN_INTERVAL, MAX_INTERVAL)
    _glitches[name] = g
    _glitches[name] = Glitch(name=name, module=module, kwargs=kwargs)

def start(name: str, duration: float):
    """Mark a glitch as running for a given duration."""
    g = _glitches.get(name)
    if g and g.enabled:
        g.running = True
        g.start_time = time.time()
        g.duration = duration

def stop(name: str):
    """Stop a glitch immediately."""
    g = _glitches.get(name)
    if g:
        g.running = False
        g.start_time = None
        g.duration = None

def _glitch_desaturate(frame, **kwargs):
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
    return frame

def _glitch_oversaturate(frame, **kwargs):
    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
    hsv[..., 1] = np.clip(hsv[..., 1] * 2.0, 0, 255)
    frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    return frame

def _glitch_color_shift(frame, **kwargs):
    b, g, r = cv2.split(frame)
    frame = cv2.merge([g, r, b])
    return frame

def _glitch_contrast(frame, **kwargs):
    alpha = random.uniform(0.5, 1.5)
    frame = cv2.convertScaleAbs(frame, alpha=alpha, beta=0)
    return frame

def _glitch_whitenoise(frame, **kwargs):
    intensity = random.randint(32, 128)
    noise = np.random.randint(0, intensity, frame.shape, dtype='uint8')
    frame = cv2.add(frame, noise)
    return frame

def _glitch_tearing(frame, **kwargs):
    rows, cols, _ = frame.shape
    num_slices = random.randint(3, 8)  # number of tearing "slices"
    tear_image = frame.copy()

    for _ in range(num_slices):
        y = random.randint(0, rows - 20)
        h = random.randint(5, 20)  # height of tear band
        shift = random.randint(-30, 30)  # how much to horizontally offset

        # Shift the band horizontally
        tear_image[y:y+h, :] = np.roll(tear_image[y:y+h, :], shift, axis=1)

        # Add a thin black line above or below to simulate a gap
        gap_position = y + h if (y + h) < rows else y - 1
        gap_thickness = random.randint(1, 3)
        gap_color = random.randint(0, 30)  # very dark gray instead of pure black
        if 0 <= gap_position < rows - gap_thickness:
            tear_image[gap_position:gap_position+gap_thickness, :] = gap_color

    return tear_image

def _glitch_vertical_hold(frame, **kwargs):
    """Simulate vertical hold loss by rolling the image up or down."""
    h, w, c = frame.shape

    # Pick a random vertical shift (somewhere within ~1/3 of the frame height)
    shift = random.randint(-h // 3, h // 3)

    # Use numpy.roll to wrap vertically
    glitched = np.roll(frame, shift, axis=0)

    # Optional: add a little jitter/noise to mimic instability
    if random.random() < 0.3:  # 30% chance
        jitter = random.randint(-5, 5)
        glitched = np.roll(glitched, jitter, axis=0)

    return glitched

def _glitch_scanlines(frame, t=None, mode="static", speed=60, **kwargs):
    """
    Overlay scanlines to simulate a CRT display.

    Parameters
    ----------
    frame : np.ndarray
        Input video frame.
    t : float
        Elapsed time in seconds (from glitch system clock).
    mode : str
        "static" -> darkens fixed rows
        "scroll" -> scanlines scroll down the screen
    speed : float
        Scroll speed in lines per second (only for scroll mode).
    """
    h, w, c = frame.shape
    output = frame.copy()

    if mode == "static":
        # Darken every other row
        output[::2, :, :] = (output[::2, :, :] * 0.5).astype(np.uint8)

    elif mode == "scroll" and t is not None:
        # Offset based on elapsed time
        offset = int((t * speed)) % 2
        output[offset::2, :, :] = (output[offset::2, :, :] * 0.5).astype(np.uint8)

    return output

last_trigger_time = 0.0
next_trigger_interval = random.uniform(5.0, 10.0)  # first interval randomized

def apply(frame):
    """Apply active glitches to a frame, possibly starting new ones."""
    now = time.time()

    # 1. Update running glitches
    for glitch in _glitches.values():
        if glitch.running and now - glitch.start_time >= glitch.duration:
            glitch.running = False

    # 2. Maybe trigger new glitches
    for glitch in _glitches.values():
        if glitch.enabled and not glitch.running:
            if now - glitch.start_time >= glitch.trigger_interval:
                glitch.running = True
                glitch.start_time = now
                glitch.duration = random.uniform(MIN_DURATION, MAX_DURATION)          # global duration range
                glitch.trigger_interval = random.uniform(MIN_INTERVAL, MAX_INTERVAL)  # global interval range

    # 3. Apply all currently running glitches
    for glitch in _glitches.values():
        if glitch.running:
            func: Callable = getattr(_module, f"_glitch_{glitch.name}")
            elapsed = now - glitch.start_time
            frame = func(frame, t=elapsed, **glitch.kwargs)

    return frame

def scheduler():
    """Start glitches at randomized time intervals (not per frame)."""
    global last_trigger_time, next_trigger_interval, _seq_index

    now = time.time()
    if now - last_trigger_time < next_trigger_interval:
        return  # wait until next trigger window

    last_trigger_time = now
    next_trigger_interval = random.uniform(1.0, 30.0)  # pick new gap for next time

    # Pick eligible glitches
    eligible = [g for g in _glitches.values() if g.enabled and not g.running]
    if not eligible:
        return

    if _sequential_mode:
        g = eligible[_seq_index % len(eligible)]
        _seq_index += 1
    else:
        g = random.choice(eligible)

    # Pick random duration for this glitch
    duration = random.uniform(1.0, 4.0)
    start(g.name, duration)


for g in ['desaturate', 'oversaturate', 'color_shift', 'contrast', 'whitenoise', 'tearing', 'vertical_hold', 'scanlines']:
    register(g)
