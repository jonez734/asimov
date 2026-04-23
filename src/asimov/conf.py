# asimov/conf.py
# Central configuration for Asimov

import copy
import json
import logging
import os
import threading
from pathlib import Path

# ------------------------------------------------------------
# Thread Safety
# ------------------------------------------------------------

_conf_lock = threading.RLock()
_conf_changed = threading.Event()

# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------

LOGGER_NAME = "asimov"
_config_logger = logging.getLogger("asimov.conf")

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
# Hand / Finger Detection
# ------------------------------------------------------------

HAND = {
    "ENABLED": True,
    "MODEL_COMPLEXITY": 1,
    "MIN_DETECTION_CONFIDENCE": 0.5,
    "MIN_TRACKING_CONFIDENCE": 0.5,
    "DETECTION_CON": 0.6,
    "USE_OVERLAY": False,
    "OVERLAY_ALPHA": 0.7,
    "TEXT_COLOR": (0, 255, 0),
    "DETECTION": {
        "MIN_DETECTION_CONF": 0.7,
        "MAX_HANDS": 1,
    },
    "FILTER": {
        "FREQ": 30.0,
        "MIN_CUTOFF": 1.0,
        "BETA": 0.0,
    },
    "DRAW": {
        "SHOW_LANDMARKS": True,
        "SHOW_BBOX": False,
        "DRAW_HANDEDNESS": True,
        "DRAW_SKELETON": True,
        "DRAW_CONFIDENCE": False,
    },
    "DEBUG": {
        "SHOW_FPS": False,
    },
}

# ------------------------------------------------------------
# INDEX FINGERTIP (ABI-STABLE)
# ------------------------------------------------------------
# NOTE:
# This configuration is consumed by multiple modules:
#   - indexfingertip
#   - rect / touch
#   - gesture / future modules
#
# DO NOT REMOVE OR RENAME KEYS without coordinated migration.

INDEXFINGERTIP = {
    # --------------------------------------------------------
    # Detection settings
    # --------------------------------------------------------
    "DETECTION": {
        "DETECTION_CON": 0.6,
    },
    # --------------------------------------------------------
    # Update / sampling frequency (Hz)
    # Used to throttle detection or smoothing
    # --------------------------------------------------------
    "FREQ": 30,
    # --------------------------------------------------------
    # Temporal filtering (EMA-style smoothing)
    # --------------------------------------------------------
    "FILTER": {
        "enabled": True,
        "alpha": 0.4,  # smoothing factor
        "deadzone": 2,  # pixels
        "FREQ": 30.0,  # Hz (can mirror INDEXFINGERTIP.FREQ)
        "MIN_CUTOFF": 1.0,  # minimum cutoff frequency
        "BETA": 0.0,  # speed coefficient
        # Optional but commonly used
        "D_CUTOFF": 1.0,  # derivative cutoff frequency
    },
    # --------------------------------------------------------
    # Optional drawing / debug visualization
    # --------------------------------------------------------
    "DRAW": {
        "enabled": True,
        "radius": 6,
        "color": (0, 255, 0),
        "thickness": -1,
    },
}

# ------------------------------------------------------------
# FPS Overlay
# ------------------------------------------------------------

FPS_OVERLAY = {
    "DRAW": {
        "enabled": True,
        "pos": (10, 80),
        "bg_color": (255, 0, 255),
        "text_color": (255, 255, 255),
        "scale": 1.0,
        "thickness": 2,
    },
}

# ------------------------------------------------------------
# Rect / Touch Interaction
# ------------------------------------------------------------

RECT = {
    "COLOR": (0, 180, 255),
    "TOUCHED_COLOR": (0, 0, 255),
    "THICKNESS": 2,
    "TOUCHED_THICKNESS": 3,
    "LABEL_SCALE": 0.5,
    "LABEL_THICKNESS": 1,
}

RECT_TOUCH = {
    "DETECTION": {
        "enabled": True,
    },
}


# ------------------------------------------------------------
# Glitch system (already partially restored elsewhere)
# ------------------------------------------------------------

GLITCH_DEFAULT_MODULE = "asimov.modules.glitch"

GLITCH_DEFAULT_MAX_CONCURRENT = 2
GLITCH_DEFAULT_VHS_INTENSITY = 5
GLITCH_DEFAULT_VHS_FREQ = 1.5
GLITCH_DEFAULT_DATAMOSH_INTENSITY = 0.3
GLITCH_DEFAULT_DATAMOSH_STRIPS = 6
GLITCH_DEFAULT_GHOST_ALPHA = 0.4
GLITCH_DEFAULT_GHOST_SHIFT = 5
GLITCH_DEFAULT_GHOST_MAXLEN = 5
GLITCH_DEFAULT_SCANLINE_STEP = 4
GLITCH_DEFAULT_SCANLINE_OPACITY = 0.7
GLITCH_DEFAULT_WHITE_NOISE_INTENSITY = 20

GLITCH = {
    "ENABLED": True,
    "MIN_INTERVAL": 2.0,
    "MAX_INTERVAL": 6.0,
    "MIN_DURATION": 0.5,
    "MAX_DURATION": 2.5,
    "MAX_CONCURRENT": GLITCH_DEFAULT_MAX_CONCURRENT,
    "DEFAULT_MODULE": GLITCH_DEFAULT_MODULE,
    "REGISTRY": {
        "vhs_warp": {"enabled": True, "weight": 1.0},
        "datamosh": {"enabled": True, "weight": 0.8},
        "ghost": {"enabled": True, "weight": 0.6},
        "scanlines": {"enabled": True, "weight": 0.4},
        "whitenoise": {"enabled": True, "weight": 0.3},
        "tearing": {"enabled": True, "weight": 0.3},
        "color_shift": {"enabled": True, "weight": 0.3},
        "vertical_hold": {"enabled": True, "weight": 0.2},
    },
}


# ------------------------------------------------------------
# OVERLAYS (ABI-STABLE)
# ------------------------------------------------------------
# NOTE:
# This registry is part of the public Asimov configuration ABI.
# It is consumed by main_generic and multiple modules.
# DO NOT REMOVE OR REFACTOR without coordinated migration.

OVERLAYS = {
    # Example overlays; adjust enable/order as needed
    "fps_overlay": {
        "module_path": "asimov.modules.fps_overlay",
        "enabled": False,
        "order": 5,
        "hotkey": "",
    },
    "hand": {
        "module_path": "asimov.modules.hand",
        "enabled": True,
        "order": 10,
        "hotkey": "h",
    },
    "indexfingertip": {
        "module_path": "asimov.modules.indexfingertip",
        "enabled": True,
        "order": 20,
        "hotkey": "i",
    },
    "rect": {
        "module_path": "asimov.modules.rect",
        "enabled": True,
        "order": 25,
        "hotkey": "r",
    },
    "rect_touch": {
        "module_path": "asimov.modules.rect_touch",
        "enabled": True,
        "order": 26,
        "hotkey": "",
    },
    "face": {
        "module_path": "asimov.modules.face",
        "enabled": True,
        "order": 35,
        "hotkey": "f",
    },
    "facemask": {
        "module_path": "asimov.modules.facemask",
        "enabled": False,
        "order": 36,
        "hotkey": "",
    },
    "eyes_next": {
        "module_path": "asimov.modules.eyes_next",
        "enabled": True,
        "order": 40,
        "hotkey": "e",
    },
    ##    "motionblur": {
    ##        "module_path": "asimov.modules.motionblur",
    ##        "enabled": True,
    ##        "order": 50,
    ##        "hotkey": "m",
    ##    },
    ##    "glitch": {
    ##        "module_path": "asimov.modules.glitch",
    ##        "enabled": False,
    ##        "order": 100,
    ##        "hotkey": "g",
    ##    },
}

# ------------------------------------------------------------
# EYES (ABI-STABLE)
# ------------------------------------------------------------
# FaceMesh / cvzone / MediaPipe are used ONLY to obtain landmarks.
# All interpretation, filtering, timing, and drawing are owned by Asimov.
#
# DO NOT REMOVE OR RENAME KEYS without coordinated migration.
# DO NOT REFACTOR — required by eyes_next.py
# ---- Eyes / Privacy Bar (FaceMesh-based) ----
# ------------------------------------------------------------
# EYES (ABI-STABLE)
# ------------------------------------------------------------
# Eye privacy-bar logic (FaceMesh landmark consumer)
#
# Face acquisition is owned by conf.FACE.
# This block owns interpretation, filtering, and rendering.
#
# DO NOT REMOVE OR RENAME KEYS without migration.

EYES = {
    # --------------------------------------------------------
    # Landmark groupings (FaceMesh indices)
    # --------------------------------------------------------
    "FACEMESH": {
        "LANDMARKS": {
            "LEFT_EYE": [33, 133, 160, 159, 158, 157, 173],
            "RIGHT_EYE": [362, 263, 387, 386, 385, 384, 398],
        },
    },
    # --------------------------------------------------------
    # One Euro Filter configuration
    # --------------------------------------------------------
    "FILTER": {
        "FREQ": 60.0,  # Expected frame rate (Hz)
        "MIN_CUTOFF": 1.0,  # Smoothness
        "BETA": 0.01,  # Responsiveness
    },
    # --------------------------------------------------------
    # Privacy bar geometry & behavior
    # --------------------------------------------------------
    "BAR": {
        # Scaling relative to eye bounding box
        "WIDTH_SCALE": 1.6,
        "HEIGHT_SCALE": 2.2,
        # Rendering
        "COLOR": (0, 0, 0),  # BGR
        "ALPHA": 0.85,  # 0.0–1.0
        # Seconds to keep bar after detection loss
        "GRACE_PERIOD": 0.35,
    },
}

# ------------------------------------------------------------
# FACE (ABI-STABLE)
# ------------------------------------------------------------
# FaceMesh acquisition module
#
# Owns all MediaPipe / cvzone configuration.
# Produces raw landmarks only.
#
# DO NOT REMOVE OR RENAME KEYS without migration.

# ------------------------------------------------------------
# FACE (ABI-STABLE)
# ------------------------------------------------------------
# Face mesh acquisition
#
# Owns all mesh-detection configuration.
# Produces raw landmarks only.
#
# DO NOT REMOVE OR RENAME KEYS without migration.

FACE = {
    # --------------------------------------------------------
    # Global enable
    # --------------------------------------------------------
    "ENABLED": True,
    # --------------------------------------------------------
    # Face mesh detector configuration
    # --------------------------------------------------------
    "MESH": {
        "MAX_FACES": 1,
        # Initial detection confidence
        "DETECTION_CON": 0.5,
        # Temporal tracking confidence
        "TRACKING_CON": 0.5,
    },
    # --------------------------------------------------------
    # Output semantics
    # --------------------------------------------------------
    "OUTPUT": {
        # Publish full landmark arrays
        "LANDMARKS": True,
        # Seconds to keep last valid face data
        "GRACE_PERIOD": 0.35,
    },
    # --------------------------------------------------------
    # Debug / visualization
    # --------------------------------------------------------
    "DRAW": {
        "DETECTION": False,
        "MODE": "key",
        "DRAW_IRIS": False,
        "MIRROR": False,
        "ALPHA": 1.0,
        "COLOR": (0, 255, 0),
        "LINE_THICKNESS": 1,
        "POINT_RADIUS": 1,
    },
}

# ------------------------------------------------------------
# FACEMASK (ABI-STABLE)
# ------------------------------------------------------------
# Face mask overlay with PNG images.
#
# Requires: FACE module enabled
# Consumed by:
#   - facemask.py
#
# DO NOT REMOVE OR RENAME KEYS without coordinated migration.

FACEMASK = {
    "ENABLED": False,
    "IMAGE": {
        "IMAGE_PATH": "",
        "POSITION": "TL",
        "LANDMARK": 10,
    },
    "ADJUST": {
        "SCALE": 1.0,
        "OFFSET_X": 0,
        "OFFSET_Y": 0,
    },
}

# ------------------------------------------------------------
# MOTION BLUR (ABI-STABLE)
# ------------------------------------------------------------
# Temporal motion blur driven by fingertip velocity.
#
# Consumed by:
#   - motionblur.py
#
# DO NOT REMOVE OR RENAME KEYS without coordinated migration.

MOTIONBLUR = {
    # --------------------------------------------------------
    # Frame history
    # --------------------------------------------------------
    # Number of frames to retain for temporal accumulation
    "HISTORY_LEN": 8,
    # --------------------------------------------------------
    # Velocity → blur mapping
    # --------------------------------------------------------
    # Velocity (pixels/frame) at which blur reaches maximum
    "VELOCITY_NORM": 40.0,
    # Minimum and maximum alpha contribution of newest frame
    "ALPHA_MIN": 0.15,
    "ALPHA_MAX": 0.85,
    # --------------------------------------------------------
    # Tail behavior
    # --------------------------------------------------------
    # Minimum weight for oldest frame in history
    "TAIL_ALPHA": 0.05,
    "RADIUS": 12,
    # Directional blur
    "MAX_OFFSET": 20,  # pixels of trail at max velocity
    # Color gating
    "COLOR_GATE": True,
    "YELLOW_MIN": (20, 120, 120),  # HSV
    "YELLOW_MAX": (40, 255, 255),
    "RADIUS_MIN_FRAC": 0.006,  # % of min(frame_dim)
    "RADIUS_MAX_FRAC": 0.025,
    "RADIUS_VELOCITY_NORM": 40.0,  # velocity at which radius hits max
}

FLOAT_CARD = {
    "PALM_SCALE": 1.5,
    "OPACITY": 0.8,
    "GLITCH_OPACITY": 0.5,
    "MAX_HANDS": 1,
    "DETECTION_CON": 0.7,
}

SCENE = {
    "name": "float_card",
    "modules": [
        {
            "name": "fps_overlay",
            "module": "asimov.modules.fps_overlay",
            "conf": {},
            "enabled": True,
        },
        {
            "name": "hand",
            "module": "asimov.modules.hand",
            "conf": {},
            "enabled": True,
        },
        {
            "name": "indexfingertip",
            "module": "asimov.modules.indexfingertip",
            "conf": {},
            "enabled": True,
        },
        {
            "name": "rect",
            "module": "asimov.modules.rect",
            "conf": {},
            "enabled": False,
        },
        {
            "name": "rect_touch",
            "module": "asimov.modules.rect_touch",
            "conf": {},
            "enabled": False,
        },
        {
            "name": "face",
            "module": "asimov.modules.face",
            "conf": {},
            "enabled": True,
        },
        {
            "name": "facemask",
            "module": "asimov.modules.facemask",
            "conf": {},
            "enabled": True,
        },
        {
            "name": "eyes_next",
            "module": "asimov.modules.eyes_next",
            "conf": {},
            "enabled": False,
        },
        {
            "name": "float_playingcard",
            "module": "asimov.modules.float_playingcard",
            "conf": {},
            "enabled": False,
        },
    ],
    "conf": {
        "HAND": {"MAX_HANDS": 1},
        "FLOAT_PLAYINGCARD": {"OPACITY": 0.85},
    },
}

FLOAT_PLAYINGCARD = {
    "Card": {
        "rank": None,
        "suit": None,
        "opacity": 0.8,
    },
    "IMAGE": None,  # Set to full path, or None to use --basedir/--set-name
    "SCALE": 0.8,
    "ROTATION": 0,
    "OPACITY": 0.8,
    "FLOAT_AMPLITUDE": 12,
    "FLOAT_FREQUENCY": 0.5,
}

# ------------------------------------------------------------
# Playing Card shared config
# ------------------------------------------------------------
PLAYINGCARD = {
    "BASEDIR": "$HOME/projects/playingcarddata",
    "SET_NAME": "bicycle",
    "DETECTION_THRESHOLD": 0.8,
}

# ------------------------------------------------------------
# Thread-Safe Unified CONF
# ------------------------------------------------------------

CONF = {
    "HAND": HAND,
    "EYES": EYES,
    "FACE": FACE,
    "FACEMASK": FACEMASK,
    "RECT": RECT,
    "RECT_TOUCH": RECT_TOUCH,
    "OVERLAYS": OVERLAYS,
    "INDEXFINGERTIP": INDEXFINGERTIP,
    "FLOAT_PLAYINGCARD": FLOAT_PLAYINGCARD,
}


def get(key):
    """Atomic deep copy read from CONF."""
    with _conf_lock:
        return copy.deepcopy(CONF[key])


def set(key, value):
    """Atomic write to CONF, triggers change event."""
    with _conf_lock:
        CONF[key] = value
        _conf_changed.set()


def update(key, section, key_name, value):
    """Update a nested config value and trigger change event."""
    with _conf_lock:
        CONF[key][section][key_name] = value
        _conf_changed.set()


def notify_change():
    """Manually trigger the change event (for external config modifications)."""
    with _conf_lock:
        _conf_changed.set()


def get_overlays_items():
    """Returns sorted overlays items list for iteration."""
    with _conf_lock:
        return sorted(CONF["OVERLAYS"].items(), key=lambda x: x[1].get("order", 99))


def get_overlays_changed_event():
    """Returns Event for detection thread to poll."""
    return _conf_changed


def clear_overlays_changed():
    """Clear the change flag after refresh."""
    _conf_changed.clear()


# ------------------------------------------------------------
# External Configuration
# ------------------------------------------------------------


def _load_external_config():
    """Load external JSON config for partial override of defaults."""
    config_path = os.environ.get("ASIMOV_CONFIG")
    if config_path:
        config_file = Path(config_path)
        source = f"ASIMOV_CONFIG={config_path}"
    else:
        config_file = Path.home() / ".asimov" / "config.json"
        source = "~/.asimov/config.json (default)"

    if config_file.exists():
        try:
            with open(config_file) as f:
                data = json.load(f)
            _config_logger.info(f"Loading external config from: {config_file}")
            _config_logger.info(f"Config source: {source}")
            _config_logger.info(f"Loaded keys: {list(data.keys())}")
            return data
        except json.JSONDecodeError as e:
            _config_logger.warning(f"Invalid JSON in {config_file}: {e}, using defaults")
        except OSError as e:
            _config_logger.warning(f"Cannot read {config_file}: {e}, using defaults")
    else:
        _config_logger.debug(f"External config not found at {config_file}, using defaults")
    return {}


def _apply_external_config(external):
    """Apply external config via partial override."""
    if not external:
        return

    for key, value in external.items():
        if key in CONF:
            CONF[key].update(value)
            _config_logger.info(f"Overridden CONF['{key}']: {list(value.keys())}")
        elif key in globals() and isinstance(globals().get(key), dict):
            globals()[key].update(value)
            _config_logger.info(f"Overridden {key}: {list(value.keys())}")
        else:
            _config_logger.warning(f"Ignored unknown config key: {key}")


_external = _load_external_config()
_apply_external_config(_external)
