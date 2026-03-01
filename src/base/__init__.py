# asimov_base/__init__.py
# Base package for Asimov - shared configuration and utilities

from .conf import (
    LOGGER_NAME,
    WINDOW_NAME,
    CAPTURE_DEVICE,
    CAPTURE_WIDTH,
    CAPTURE_HEIGHT,
    CAPTURE_FPS,
)

from . import lib

try:
    from asimov.conf import SCENE
except ImportError:
    SCENE = {}

__all__ = [
    "LOGGER_NAME",
    "WINDOW_NAME",
    "CAPTURE_DEVICE",
    "CAPTURE_WIDTH",
    "CAPTURE_HEIGHT",
    "CAPTURE_FPS",
    "lib",
    "SCENE",
]