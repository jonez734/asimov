# asimov-modules Specification

## Overview

`asimov-modules` is the computer vision module package for Asimov. It provides detection and processing modules for hand tracking, face detection, fingertip detection, and various visual effects.

## Package Structure

```
modules/
├── __init__.py          # Empty
├── conf.py              # Module configuration
├── hand.py              # Hand detection module
├── face.py              # Face detection module
├── indexfingertip.py    # Index fingertip detection module
├── rect.py             # Rectangle rendering module
├── rect_touch.py       # Rectangle touch detection module
├── eyes_next.py        # Eye privacy bar module
├── fps_overlay.py      # FPS overlay module
├── glitch.py           # Glitch effect module
├── motionblur.py       # Motion blur module
├── float_card.py       # Floating card module
└── float_playingcard.py # Floating playing card module
```

## Module Interface

Each module must implement these functions:

```python
def init(args, **kwargs) -> bool:
    """Initialize module resources."""
    pass

def access(args, op, /, **kwargs) -> bool:
    """Check operation access."""
    pass

def buildargs(args, **kwargs):
    """Build argument parser. Returns ArgumentParser or None."""
    pass

def main(args, **kwargs) -> bool:
    """Main execution."""
    pass
```

Detection modules must implement:

```python
def detect(frame, context: ThreadSafeContext, **kwargs):
    """Run detection on frame, publish to context."""
    pass

def draw(frame, context: ThreadSafeContext, **kwargs) -> np.ndarray:
    """Draw overlays on frame."""
    pass
```

Optional:

```python
def ui_schema(args=None, context=None) -> dict | None:
    """Return UI schema for configuration."""
    pass
```

## Configuration (conf.py)

### Hand Detection

```python
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
```

### Index Fingertip

```python
INDEXFINGERTIP = {
    "LANDMARK_ID": 8,
    "DETECTION_CON": 0.6,
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
}
```

### Face Detection

```python
FACE = {
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
    "DRAW_DETECTION": False,
}
```

### Eyes

```python
EYES = {
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
}
```

### FPS Overlay

```python
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
```

### Rectangle

```python
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
```

### Glitch

```python
GLITCH = {
    "ENABLED": True,
    "MIN_INTERVAL": 2.0,
    "MAX_INTERVAL": 6.0,
    "MIN_DURATION": 0.5,
    "MAX_DURATION": 2.5,
    "MAX_CONCURRENT": 2,
    "DEFAULT_MODULE": "asimov_modules.glitch",
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
```

### Motion Blur

```python
MOTIONBLUR = {
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
}
```

### Float Card

```python
FLOAT_CARD = {
    "PALM_SCALE": 1.5,
    "OPACITY": 0.8,
    "GLITCH_OPACITY": 0.5,
    "MAX_HANDS": 1,
    "DETECTION_CON": 0.7,
}

FLOAT_PLAYINGCARD = {
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
}

PLAYINGCARD = {
    "BASEDIR": "$HOME/projects/playingcarddata",
    "SET_NAME": "bicycle",
    "DETECTION_THRESHOLD": 0.8,
}
```

### Overlays Registry

```python
OVERLAYS = {
    "fps_overlay": {"module_path": "asimov_modules.fps_overlay", "enabled": True, "order": 5},
    "hand": {"module_path": "asimov_modules.hand", "enabled": True, "order": 10},
    "indexfingertip": {"module_path": "asimov_modules.indexfingertip", "enabled": True, "order": 20},
    "rect": {"module_path": "asimov_modules.rect", "enabled": True, "order": 25},
    "rect_touch": {"module_path": "asimov_modules.rect_touch", "enabled": True, "order": 26},
    "face": {"module_path": "asimov_modules.face", "enabled": True, "order": 35},
    "eyes_next": {"module_path": "asimov_modules.eyes_next", "enabled": True, "order": 40},
}
```

### Default Scene

```python
SCENE = {
    "name": "float_card",
    "modules": [
        {"name": "fps_overlay", "module": "asimov_modules.fps_overlay", "conf": {}},
        {"name": "hand", "module": "asimov_modules.hand", "conf": {}},
        {"name": "rect", "module": "asimov_modules.rect", "conf": {}},
        {"name": "rect_touch", "module": "asimov_modules.rect_touch", "conf": {}},
        {"name": "float_playingcard", "module": "asimov_modules.float_playingcard", "conf": {}},
    ],
    "conf": {
        "HAND": {"MAX_HANDS": 1},
        "FLOAT_PLAYINGCARD": {"OPACITY": 0.85},
    },
}
```

## Module Descriptions

### hand.py

Hand detection using cvzone HandDetector (MediaPipe). Publishes hand landmarks and metadata to `context["HAND"]`.

- `detect()`: Run detection, store results in context
- `draw()`: Render skeleton landmarks and bounding box
- `ui_schema()`: Return configuration UI schema

### face.py

Face mesh detection using cvzone FaceMeshDetector. Publishes face landmarks to `context["FACE"]`.

- `detect()`: Run FaceMesh detection
- `draw()`: No drawing (delegated to other modules)

### indexfingertip.py

Index fingertip tracking. Consumes `context["HAND"]`, publishes to `context["INDEXFINGERTIP"]`.

- `detect()`: Extract index fingertip position from hand landmarks
- `draw()`: Draw fingertip marker

### rect.py

Rectangle rendering module. Consumes `context["INDEXFINGERTIP"]`.

- `draw()`: Draw interactive rectangles

### rect_touch.py

Rectangle touch detection. Consumes `context["INDEXFINGERTIP"]` and rectangle data.

- `detect()`: Detect fingertip-rectangle intersections

### eyes_next.py

Eye privacy bar module. Consumes `context["FACE"]`.

- `detect()`: Process face landmarks for eye positions
- `draw()`: Render privacy bars over eyes

### fps_overlay.py

FPS counter overlay.

- `draw()`: Render FPS on frame

### glitch.py

Glitch visual effects (VHS warp, datamosh, ghost, scanlines, etc.)

- `detect()`: Apply glitch effects
- `draw()`: Render glitched frame

### motionblur.py

Motion blur effect based on fingertip velocity.

- `detect()`: Calculate velocity-based blur
- `draw()`: Apply motion blur

### float_card.py

Floating card overlay on detected palm.

- `detect()`: Track palm position
- `draw()`: Render floating card

### float_playingcard.py

Floating playing card with detection.

- `detect()`: Detect and track playing card
- `draw()`: Render card with animation

## Usage Examples

### Using a Detection Module

```python
from asimov.base.common import ThreadSafeContext
from asimov.modules import hand, face

context = ThreadSafeContext()

# Run hand detection
hand.detect(frame, context)
hand.draw(frame, context)

# Run face detection
face.detect(frame, context)
```

### Module Configuration

```python
from asimov import conf

# Modify hand detection settings
conf.HAND["DETECTION"]["MAX_HANDS"] = 2
conf.HAND["FILTER"]["MIN_CUTOFF"] = 0.5
```

### Accessing Detection Results

```python
# From context
hands = context.get("HAND", {}).get("hands", [])
faces = context.get("FACE", {}).get("faces", [])
fingertip = context.get("INDEXFINGERTIP", {}).get("position")
```
