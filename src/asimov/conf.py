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

CAPTURE_DEVICE = 0
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
    "USE_OVERLAY": True,
    "OVERLAY_ALPHA": 0.7,
    "DRAW_HANDEDNESS": True,
    "DRAW_SKELETON": True,
    "DRAW_CONFIDENCE": False,
    "TEXT_COLOR": (0, 255, 0),
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

#    "rect": {
#        "module_path": "asimov.rect",
#        "enabled": True,
#        "order": 30,
#        "hotkey": "r",
#    },
    "face": {
        "module_path": "asimov.modules.face",
        "enabled": True,
        "order": 35,
        "hotkey": "f",
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
            "LEFT_EYE": [
                33, 133, 160, 159, 158, 157, 173
            ],
            "RIGHT_EYE": [
                362, 263, 387, 386, 385, 384, 398
            ],
        },
    },

    # --------------------------------------------------------
    # One Euro Filter configuration
    # --------------------------------------------------------
    "FILTER": {
        "FREQ": 60.0,        # Expected frame rate (Hz)
        "MIN_CUTOFF": 1.0,   # Smoothness
        "BETA": 0.01,        # Responsiveness
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
        "ALPHA": 0.85,       # 0.0–1.0

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
    "DRAW_DETECTION": False,
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
    "MAX_OFFSET": 20,   # pixels of trail at max velocity

    # Color gating
    "COLOR_GATE": True,
    "YELLOW_MIN": (20, 120, 120),   # HSV
    "YELLOW_MAX": (40, 255, 255),

    "RADIUS_MIN_FRAC": 0.006,   # % of min(frame_dim)
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
            "name": "hand",
            "module": "asimov.modules.hand",
            "conf": {},
        },
        {
            "name": "float_playingcard",
            "module": "asimov.modules.float_playingcard",
            "conf": {},
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
