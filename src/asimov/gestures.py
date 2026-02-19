# File: asimov/gestures.py

import time
import math

from .common import safe_distance

# --- Named constants ---
DEFAULT_PINCH_THRESHOLD = 30
DEFAULT_DEBOUNCE_TIME = 0.4  # seconds

# --- Gesture state management ---

class GestureState:
    """Tracks time-based gesture events like pinch, spread, etc.
    Provides debounce protection so gestures don’t repeat too quickly.
    """

    def __init__(self, debounce_time=DEFAULT_DEBOUNCE_TIME):
        self.debounce_time = debounce_time
        self.last_trigger = {}

    def can_trigger(self, gesture_name):
        """Return True if enough time has passed to allow this gesture."""
        now = time.monotonic()
        last = self.last_trigger.get(gesture_name, 0)
        return (now - last) >= self.debounce_time

    def mark_trigger(self, gesture_name):
        """Record that a gesture just triggered."""
        self.last_trigger[gesture_name] = time.monotonic()

    def try_trigger(self, gesture_name):
        """Return True and record if allowed; otherwise False."""
        if self.can_trigger(gesture_name):
            self.mark_trigger(gesture_name)
            return True
        return False
