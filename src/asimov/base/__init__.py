# asimov/base/__init__.py
# Base package for Asimov - shared configuration and utilities

from ..conf import (  # noqa: F811
    CAPTURE_DEVICE,
    CAPTURE_FPS,
    CAPTURE_HEIGHT,
    CAPTURE_WIDTH,
    LOGGER_NAME,
    SCENE,
    WINDOW_NAME,
)

from . import lib

__all__ = [
    "conf",
    "lib",
    "LOGGER_NAME",
    "WINDOW_NAME",
    "CAPTURE_DEVICE",
    "CAPTURE_WIDTH",
    "CAPTURE_HEIGHT",
    "CAPTURE_FPS",
    "SCENE",
]