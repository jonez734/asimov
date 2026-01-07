# asimov/conf.py
# Central configuration for Asimov
# This file is intentionally explicit and redundant for ABI stability

# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------

# DO NOT REMOVE OR REFACTOR
# Used by logging, io, and external tooling
LOGGER_NAME = "asimov"

# ------------------------------------------------------------
# Window / UI
# ------------------------------------------------------------

WINDOW_NAME = "Asimov Preview"

# ------------------------------------------------------------
# Capture defaults
# ------------------------------------------------------------

CAPTURE_DEVICE = 1
CAPTURE_WIDTH  = 640
CAPTURE_HEIGHT = 480
CAPTURE_FPS    = 30

# ------------------------------------------------------------
# Hand / Finger Detection
# ------------------------------------------------------------

HAND = {
    "ENABLED": True,
    "MAX_HANDS": 1,
    "MODEL_COMPLEXITY": 1,
    "MIN_DETECTION_CONFIDENCE": 0.5,
    "MIN_TRACKING_CONFIDENCE": 0.5,
    "DETECTION_CON": 0.6,

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
    # MediaPipe landmark index
    # --------------------------------------------------------
    "LANDMARK_ID": 8,

    # --------------------------------------------------------
    # Detection confidence threshold
    # Used to gate whether fingertip data is considered valid
    # --------------------------------------------------------
    "DETECTION_CON": 0.6,

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
        "alpha": 0.4,      # smoothing factor
        "deadzone": 2,     # pixels
        "FREQ": 30.0,        # Hz (can mirror INDEXFINGERTIP.FREQ)
        "MIN_CUTOFF": 1.0,   # minimum cutoff frequency
        "BETA": 0.0,         # speed coefficient

        # Optional but commonly used
        "D_CUTOFF": 1.0,     # derivative cutoff frequency
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
# Rect / Touch Interaction
# ------------------------------------------------------------

RECT = {
    "COLOR": (0, 180, 255),
    "TOUCHED_COLOR": (0, 0, 255),
    "THICKNESS": 2,
}


# ------------------------------------------------------------
# Glitch system (already partially restored elsewhere)
# ------------------------------------------------------------

GLITCH_DEFAULT_MODULE = "asimov.glitch"

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

    "hand": {
        "module_path": "asimov.hand",
        "enabled": True,
        "order": 10,
        "hotkey": "h",
    },

    "indexfingertip": {
        "module_path": "asimov.indexfingertip",
        "enabled": True,
        "order": 20,
        "hotkey": "i",
    },

#    "rect": {
#        "module_path": "asimov.rect",
#        "enabled": True,
#        "order": 30,
#        "hotkey": "r",
#    },
    "eyes_next": {
        "module_path": "asimov.eyes_next",
        "enabled": True,
        "order": 40,
        "hotkey": "e",
    },
    "glitch": {
        "module_path": "asimov.glitch",
        "enabled": True,
        "order": 90,
        "hotkey": "g",
    },
}

# ------------------------------------------------------------
# EYES (ABI-STABLE)
# ------------------------------------------------------------
# FaceMesh / cvzone / MediaPipe are used ONLY to obtain landmarks.
# All interpretation, filtering, timing, and drawing are owned by Asimov.
#
# DO NOT REMOVE OR RENAME KEYS without coordinated migration.
# ---- Eyes / Privacy Bar (FaceMesh-based) ----

EYES = {
    # --- FaceMesh configuration ---
    "FACEMESH": {
        "MAX_FACES": 1,

        # cvzone FaceMeshDetector params
        "DETECTION_CON": 0.5,
        "TRACKING_CON": 0.5,

        # Landmark indices for each eye
        # These must be lists of FaceMesh landmark indices
        "LANDMARKS": {
            "LEFT_EYE": [
                33, 133, 160, 159, 158, 157, 173
            ],
            "RIGHT_EYE": [
                362, 263, 387, 386, 385, 384, 398
            ],
        },
    },

    # --- One Euro Filter configuration ---
    "FILTER": {
        "FREQ": 60.0,        # Expected frame rate
        "MIN_CUTOFF": 1.0,   # Smoothness
        "BETA": 0.01,        # Responsiveness to movement
    },

    # --- Privacy bar geometry ---
    "BAR": {
        # Scaling relative to detected eye bounding box
        "WIDTH_SCALE": 1.6,
        "HEIGHT_SCALE": 2.2,

        # RGBA-like rendering
        "COLOR": (0, 0, 0),   # BGR tuple for OpenCV
        "ALPHA": 0.85,        # 0.0–1.0

        # Seconds to keep last-known bar if detection drops
        "GRACE_PERIOD": 0.35,
    },

    # --- Debug / visualization ---
    "DRAW_DETECTION": False,
}
