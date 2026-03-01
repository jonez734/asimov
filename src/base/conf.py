# asimov_base/conf.py
# Shared configuration for Asimov packages

# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------

LOGGER_NAME = "asimov"

# ------------------------------------------------------------
# Window / UI
# ------------------------------------------------------------

WINDOW_NAME = "Asimov Preview"

# ------------------------------------------------------------
# Capture defaults
# ------------------------------------------------------------

CAPTURE_DEVICE = 0
CAPTURE_WIDTH = 640
CAPTURE_HEIGHT = 480
CAPTURE_FPS = 30

# ------------------------------------------------------------
# Additional configuration (imported from asimov.conf)
# ------------------------------------------------------------

try:
    from asimov.conf import SCENE, PLAYINGCARD, FLOAT_PLAYINGCARD, GLITCH
except ImportError:
    SCENE = {}
    PLAYINGCARD = {}
    FLOAT_PLAYINGCARD = {}
    GLITCH = {}
