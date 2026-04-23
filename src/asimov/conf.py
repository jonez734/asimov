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
# Unified Configuration
# ------------------------------------------------------------

CONF = {
    "CAPTURE": {
        "DEVICE": 0,
        "WIDTH": 640,
        "HEIGHT": 480,
        "FPS": 30,
    },
    "UI": {
        "WINDOW_NAME": "Asimov Preview",
    },
    "HAND": {
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
    },
    "INDEXFINGERTIP": {
        "DETECTION": {
            "DETECTION_CON": 0.6,
        },
        "FREQ": 30,
        "FILTER": {
            "enabled": True,
            "alpha": 0.4,
            "deadzone": 2,
            "FREQ": 30.0,
            "MIN_CUTOFF": 1.0,
            "BETA": 0.0,
            "D_CUTOFF": 1.0,
        },
        "DRAW": {
            "enabled": True,
            "radius": 6,
            "color": (0, 255, 0),
            "thickness": -1,
        },
    },
    "FPS_OVERLAY": {
        "DRAW": {
            "enabled": True,
            "pos": (10, 80),
            "bg_color": (255, 0, 255),
            "text_color": (255, 255, 255),
            "scale": 1.0,
            "thickness": 2,
        },
    },
    "RECT": {
        "COLOR": (0, 180, 255),
        "TOUCHED_COLOR": (0, 0, 255),
        "THICKNESS": 2,
        "TOUCHED_THICKNESS": 3,
        "LABEL_SCALE": 0.5,
        "LABEL_THICKNESS": 1,
    },
    "RECT_TOUCH": {
        "DETECTION": {
            "enabled": True,
        },
    },
    "GLITCH": {
        "ENABLED": True,
        "MIN_INTERVAL": 2.0,
        "MAX_INTERVAL": 6.0,
        "MIN_DURATION": 0.5,
        "MAX_DURATION": 2.5,
        "MAX_CONCURRENT": 2,
        "DEFAULT_MODULE": "asimov.modules.glitch",
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
    },
    "OVERLAYS": {
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
    },
    "EYES": {
        "FACEMESH": {
            "LANDMARKS": {
                "LEFT_EYE": [33, 133, 160, 159, 158, 157, 173],
                "RIGHT_EYE": [362, 263, 387, 386, 385, 384, 398],
            },
        },
        "FILTER": {
            "FREQ": 60.0,
            "MIN_CUTOFF": 1.0,
            "BETA": 0.01,
        },
        "BAR": {
            "WIDTH_SCALE": 1.6,
            "HEIGHT_SCALE": 2.2,
            "COLOR": (0, 0, 0),
            "ALPHA": 0.85,
            "GRACE_PERIOD": 0.35,
        },
    },
    "FACE": {
        "ENABLED": True,
        "MESH": {
            "MAX_FACES": 1,
            "DETECTION_CON": 0.5,
            "TRACKING_CON": 0.5,
        },
        "OUTPUT": {
            "LANDMARKS": True,
            "GRACE_PERIOD": 0.35,
        },
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
    },
    "FACEMASK": {
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
    },
    "MOTIONBLUR": {
        "HISTORY_LEN": 8,
        "VELOCITY_NORM": 40.0,
        "ALPHA_MIN": 0.15,
        "ALPHA_MAX": 0.85,
        "TAIL_ALPHA": 0.05,
        "RADIUS": 12,
        "MAX_OFFSET": 20,
        "COLOR_GATE": True,
        "YELLOW_MIN": (20, 120, 120),
        "YELLOW_MAX": (40, 255, 255),
        "RADIUS_MIN_FRAC": 0.006,
        "RADIUS_MAX_FRAC": 0.025,
        "RADIUS_VELOCITY_NORM": 40.0,
    },
    "FLOAT_CARD": {
        "PALM_SCALE": 1.5,
        "OPACITY": 0.8,
        "GLITCH_OPACITY": 0.5,
        "MAX_HANDS": 1,
        "DETECTION_CON": 0.7,
    },
    "SCENE": {
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
    },
    "FLOAT_PLAYINGCARD": {
        "Card": {
            "rank": None,
            "suit": None,
            "opacity": 0.8,
        },
        "IMAGE": None,
        "SCALE": 0.8,
        "ROTATION": 0,
        "OPACITY": 0.8,
        "FLOAT_AMPLITUDE": 12,
        "FLOAT_FREQUENCY": 0.5,
    },
    "PLAYINGCARD": {
        "BASEDIR": "$HOME/projects/playingcarddata",
        "SET_NAME": "bicycle",
        "DETECTION_THRESHOLD": 0.8,
    },
}

# ------------------------------------------------------------
# Backward Compatibility Aliases
# NOTE: These bypass the lock and are NOT thread-safe.
# Use getters/setters for thread-safe access.
# ------------------------------------------------------------

CAPTURE_DEVICE = CONF["CAPTURE"]["DEVICE"]
CAPTURE_WIDTH = CONF["CAPTURE"]["WIDTH"]
CAPTURE_HEIGHT = CONF["CAPTURE"]["HEIGHT"]
CAPTURE_FPS = CONF["CAPTURE"]["FPS"]
WINDOW_NAME = CONF["UI"]["WINDOW_NAME"]

HAND = CONF["HAND"]
INDEXFINGERTIP = CONF["INDEXFINGERTIP"]
FPS_OVERLAY = CONF["FPS_OVERLAY"]
RECT = CONF["RECT"]
RECT_TOUCH = CONF["RECT_TOUCH"]
GLITCH = CONF["GLITCH"]
OVERLAYS = CONF["OVERLAYS"]
EYES = CONF["EYES"]
FACE = CONF["FACE"]
FACEMASK = CONF["FACEMASK"]
MOTIONBLUR = CONF["MOTIONBLUR"]
FLOAT_CARD = CONF["FLOAT_CARD"]
SCENE = CONF["SCENE"]
FLOAT_PLAYINGCARD = CONF["FLOAT_PLAYINGCARD"]
PLAYINGCARD = CONF["PLAYINGCARD"]

# ------------------------------------------------------------
# Thread-Safe Getters and Setters
# ------------------------------------------------------------


def get_capture(key: str, default=None):
    """Thread-safe getter for CAPTURE settings."""
    with _conf_lock:
        return CONF["CAPTURE"].get(key, default)


def set_capture(key: str, value):
    """Thread-safe setter for CAPTURE settings."""
    with _conf_lock:
        CONF["CAPTURE"][key] = value
        _conf_changed.set()


def get_ui(key: str, default=None):
    """Thread-safe getter for UI settings."""
    with _conf_lock:
        return CONF["UI"].get(key, default)


def set_ui(key: str, value):
    """Thread-safe setter for UI settings."""
    with _conf_lock:
        CONF["UI"][key] = value
        _conf_changed.set()


def get_module(key: str):
    """Thread-safe getter for module config (deep copy)."""
    with _conf_lock:
        return copy.deepcopy(CONF[key])


def get(key: str, default=None):
    """Thread-safe generic getter for any top-level key."""
    with _conf_lock:
        value = CONF.get(key, default)
        if isinstance(value, dict):
            return copy.deepcopy(value)
        return value


def set_module(key: str, value: dict):
    """Thread-safe setter for module config."""
    with _conf_lock:
        CONF[key] = value
        _conf_changed.set()


def update_module(key: str, updates: dict):
    """Thread-safe partial update for module config."""
    with _conf_lock:
        CONF[key].update(updates)
        _conf_changed.set()


def update(key: str, section: str, key_name: str, value):
    """Thread-safe nested update for module config section."""
    with _conf_lock:
        CONF[key][section][key_name] = value
        _conf_changed.set()


def notify_change():
    """Manually trigger the change event."""
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


def _apply_external_config(external: dict):
    """Apply external config via partial override (thread-safe)."""
    if not external:
        return

    with _conf_lock:
        for key, value in external.items():
            if key in CONF and isinstance(CONF[key], dict):
                CONF[key].update(value)
                _config_logger.info(f"Overridden {key}: {list(value.keys())}")
            else:
                _config_logger.warning(f"Ignored unknown config key: {key}")
        _conf_changed.set()


_external = _load_external_config()
_apply_external_config(_external)