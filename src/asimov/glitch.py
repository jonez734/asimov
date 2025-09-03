import cv2
import random
import time
import importlib
from dataclasses import dataclass, field
from typing import Optional, Callable
import numpy as np

@dataclass
class Glitch:
    name: str
    enabled: bool = True
    running: bool = False
    start_time: Optional[float] = None
    duration: Optional[float] = None
    module: str = "asimov.glitch"   # module where the glitch function lives
    func: Optional[Callable] = field(default=None, repr=False)

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
glitches: dict[str, Glitch] = {}
sequential_mode: bool = False
_seq_index: int = 0

def register(name: str, module: str = "asimov.glitch"):
    """Register a glitch by name (function resolved later)."""
    glitches[name] = Glitch(name=name, module=module)

def start(name: str, duration: float):
    """Mark a glitch as running for a given duration."""
    g = glitches.get(name)
    if g and g.enabled:
        g.running = True
        g.start_time = time.time()
        g.duration = duration


def stop(name: str):
    """Stop a glitch immediately."""
    g = glitches.get(name)
    if g:
        g.running = False
        g.start_time = None
        g.duration = None

def _glitch_desaturate(frame):
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
    return frame

def _glitch_oversaturate(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
    hsv[..., 1] = np.clip(hsv[..., 1] * 2.0, 0, 255)
    frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    return frame

def _glitch_color_shift(frame):
    b, g, r = cv2.split(frame)
    frame = cv2.merge([g, r, b])
    return frame

def _glitch_contrast(frame):
    alpha = random.uniform(0.5, 1.5)
    frame = cv2.convertScaleAbs(frame, alpha=alpha, beta=0)
    return frame

def _glitch_whitenoise(frame):
    intensity = random.randint(32, 128)
    noise = np.random.randint(0, intensity, frame.shape, dtype='uint8')
    frame = cv2.add(frame, noise)
    return frame

def _glitch_tearing(frame):
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

last_trigger_time = 0.0
next_trigger_interval = random.uniform(1.0, 5.0)  # first interval randomized

def apply(frame):
    """Apply all currently running glitches to the frame, time-based."""
    now = time.time()

    # Expire finished glitches
    for g in glitches.values():
        if g.running and g.duration is not None:
            if now - g.start_time >= g.duration:
                stop(g.name)

    # Apply all still-running glitches
    for g in glitches.values():
        if g.running:
            func = g.resolve_func()
            frame = func(frame)

    return frame

def scheduler():
    """Start glitches at randomized time intervals (not per frame)."""
    global last_trigger_time, next_trigger_interval, _seq_index

    now = time.time()
    if now - last_trigger_time < next_trigger_interval:
        return  # wait until next trigger window

    last_trigger_time = now
    next_trigger_interval = random.uniform(1.0, 5.0)  # pick new gap for next time

    # Pick eligible glitches
    eligible = [g for g in glitches.values() if g.enabled and not g.running]
    if not eligible:
        return

    if sequential_mode:
        g = eligible[_seq_index % len(eligible)]
        _seq_index += 1
    else:
        g = random.choice(eligible)

    # Pick random duration for this glitch
    duration = random.uniform(1.0, 4.0)
    start(g.name, duration)

for g in ['desaturate', 'oversaturate', 'color_shift', 'contrast', 'whitenoise', 'tearing']:
    register(g)
