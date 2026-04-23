# asimov/base/__init__.py
# Base package for Asimov - shared configuration and utilities

from .. import conf
from . import lib

CAPTURE_DEVICE = conf.CONF["CAPTURE"]["DEVICE"]
CAPTURE_WIDTH = conf.CONF["CAPTURE"]["WIDTH"]
CAPTURE_HEIGHT = conf.CONF["CAPTURE"]["HEIGHT"]
CAPTURE_FPS = conf.CONF["CAPTURE"]["FPS"]
WINDOW_NAME = conf.CONF["UI"]["WINDOW_NAME"]
SCENES = conf.CONF.get("SCENES", {})
SCENE = SCENES.get(SCENES.get("active", "float_card"), {})
LOGGER_NAME = "asimov"

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
    "SCENES",
]
