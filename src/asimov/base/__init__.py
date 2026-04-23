# asimov/base/__init__.py
# Base package for Asimov - shared configuration and utilities

from .. import conf

CAPTURE_DEVICE = conf.CONF["CAPTURE"]["DEVICE"]
CAPTURE_WIDTH = conf.CONF["CAPTURE"]["WIDTH"]
CAPTURE_HEIGHT = conf.CONF["CAPTURE"]["HEIGHT"]
CAPTURE_FPS = conf.CONF["CAPTURE"]["FPS"]
WINDOW_NAME = conf.CONF["UI"]["WINDOW_NAME"]
SCENE = conf.CONF["SCENE"]
LOGGER_NAME = "asimov"

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
