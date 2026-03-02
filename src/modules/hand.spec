# hand Specification

## Overview

`hand` is the authoritative hand detection module for Asimov. It owns the HandDetector (cvzone / MediaPipe), runs detection exactly once per frame, and publishes raw hand geometry + metadata into context.

**Important**: Other modules (indexfingertip, pinch, gestures, float_playingcard, etc.) must CONSUME `context["HAND"]` and must NOT run their own hand detection.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    detect(frame, context)                   │
├─────────────────────────────────────────────────────────────┤
│  1. Initialize detector (once, stored in context)          │
│  2. Run HandDetector.findHands()                         │
│  3. Publish results to context["HAND"]                    │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                    draw(frame, context)                    │
├─────────────────────────────────────────────────────────────┤
│  1. Draw skeleton landmarks (from lmList)                │
│  2. Draw bounding box (if enabled)                       │
│  3. Draw text annotations (handedness, confidence)        │
└─────────────────────────────────────────────────────────────┘
```

## Architectural Principle

**detect() must NEVER draw on the frame.** The detect phase is for detection/processing only. All visual rendering must happen in draw().

This ensures:
- Clean separation of concerns
- Modules can run in different threads without frame corruption
- Frame is not mutated during detection phase

## Frame Flip Handling

The module uses `flipType=True` with cvzone's HandDetector. This corrects handedness labels when the frame is mirrored for display.

**Important**: The frame flip (mirroring) should happen AFTER modules run, in the main loop. This ensures:
1. Detection runs on raw (unflipped) frame
2. Labels are correctly flipped by flipType=True
3. Frame is mirrored only for display

## Landmark Drawing

The module draws skeleton landmarks manually using the 21 MediaPipe landmark coordinates stored in `hand["lmList"]`. This avoids alpha blending issues with cvzone's overlay.

**Important**: cvzone's `lmList` returns pixel coordinates `[x, y, z]`, not normalized 0-1 values. The drawing code must use these values directly without scaling.

- **Landmarks**: Circles at each of the 21 hand landmark points
- **Skeleton lines**: Connections between landmark points following MediaPipe hand topology:
  - Wrist (0) to all finger bases
  - Each finger: base → MCP → PIP → DIP → TIP
  - Thumb: CMC → MCP → IP → TIP

## MediaPipe Hand Landmarks

```
        8   12  16  20      (Fingertips)
        |   |   |   |
        7   11  15  19      (DIP)
        |   |   |   |
        6   10  14  18      (PIP)
        |   |   |   |
        5---9---13--17      (MCP)
        |
        4                   (Thumb TIP)
        |
        3                   (Thumb IP)
        |
        2                   (Thumb MCP)
        |
    1---0                   (Wrist)
        |
        1                   (Thumb CMC)
```

### Landmark Indices

| Index | Name         | Finger     |
|-------|--------------|------------|
| 0     | WRIST        | -          |
| 1     | THUMB_CMC    | Thumb      |
| 2     | THUMB_MCP    | Thumb      |
| 3     | THUMB_IP     | Thumb      |
| 4     | THUMB_TIP    | Thumb      |
| 5     | INDEX_MCP    | Index      |
| 6     | INDEX_PIP    | Index      |
| 7     | INDEX_DIP    | Index      |
| 8     | INDEX_TIP    | Index      |
| 9     | MIDDLE_MCP   | Middle     |
| 10    | MIDDLE_PIP   | Middle     |
| 11    | MIDDLE_DIP   | Middle     |
| 12    | MIDDLE_TIP   | Middle     |
| 13    | RING_MCP     | Ring       |
| 14    | RING_PIP     | Ring       |
| 15    | RING_DIP     | Ring       |
| 16    | RING_TIP     | Ring       |
| 17    | PINKY_MCP    | Pinky      |
| 18    | PINKY_PIP    | Pinky      |
| 19    | PINKY_DIP    | Pinky      |
| 20    | PINKY_TIP    | Pinky      |

### Skeleton Connections

The module draws lines between these landmark pairs (stored in `hand["lmList"]`):

```python
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),        # Index
    (0, 9), (9, 10), (10, 11), (11, 12),   # Middle
    (0, 13), (13, 14), (14, 15), (15, 16), # Ring
    (0, 17), (17, 18), (18, 19), (19, 20), # Pinky
    (5, 9), (9, 13), (13, 17),             # Palm
]
```

## Configuration (conf.HAND)

The config is organized into nested sections: DETECTION, FILTER, DRAW, and DEBUG.

### Top-level keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| ENABLED | bool | True | Module enabled |
| MODEL_COMPLEXITY | int | 1 | MediaPipe model complexity (0, 1, 2) |
| MIN_DETECTION_CONFIDENCE | float | 0.5 | MediaPipe min detection confidence |
| MIN_TRACKING_CONFIDENCE | float | 0.5 | MediaPipe min tracking confidence |
| DETECTION_CON | float | 0.6 | cvzone detection confidence |
| TEXT_COLOR | tuple | (0, 255, 0) | Text annotation color (BGR) |

### DETECTION

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| MIN_DETECTION_CONF | float | 0.7 | Minimum detection confidence |
| MAX_HANDS | int | 1 | Maximum hands to detect |

### FILTER

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| FREQ | float | 30.0 | Filter frequency (Hz) |
| MIN_CUTOFF | float | 1.0 | Minimum cutoff frequency |
| BETA | float | 0.0 | Speed sensitivity |

### DRAW

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| SHOW_LANDMARKS | bool | True | Draw hand landmarks |
| SHOW_BBOX | bool | False | Draw bounding box |
| DRAW_HANDEDNESS | bool | True | Show "Left"/"Right" label |
| DRAW_SKELETON | bool | True | Draw skeleton lines |
| DRAW_CONFIDENCE | bool | False | Show detection confidence |

### DEBUG

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| SHOW_FPS | bool | False | Show hand detection FPS |

## Module ABI

### detect(frame, context, **kwargs)
- **Input**: frame (np.ndarray), context (ThreadSafeContext)
- **Output**: Sets `context["HAND"]` dict with keys:
  - `cfg`: Config dict from conf.HAND
  - `detector`: HandDetector instance
  - `hands`: List of hand dicts from cvzone
  - `timestamp`: Detection time
  - `error_state`: bool
- **Side effects**: None. detect() must NOT modify the frame.

### draw(frame, context, **kwargs) -> np.ndarray
- **Input**: frame (BGR np.ndarray), context with `["HAND"]`
- **Output**: Returns frame with landmarks, bounding box and text annotations
- **Behavior**:
  1. Draw skeleton landmarks if SHOW_LANDMARKS enabled
  2. Draw bounding box if SHOW_BBOX enabled
  3. Draw handedness label if DRAW_HANDEDNESS enabled
  4. Draw confidence if DRAW_CONFIDENCE enabled
- **Error handling**: Shows "HAND ERROR" text if error_state is True

### ui_schema(args=None, context=None) -> dict
Returns dashboard config schema for detection, filter, draw, and debug options.

### Lifecycle Hooks

| Hook | Purpose |
|------|---------|
| init | Returns True |
| buildargs | Returns None |
| access | Returns True |
| main | Returns True |

## Context Output

After detect(), other modules can read:

```python
hand_ns = context["HAND"]
hands = hand_ns["hands"]  # List of detected hands

for hand in hands:
    lmList = hand["lmList"]    # 21 landmarks, each [x, y, z]
    bbox = hand["bbox"]        # [x, y, w, h]
    center = hand["center"]    # (cx, cy)
    hand_type = hand["type"]   # "Left" or "Right"
    confidence = hand["confidence"]  # float 0.0-1.0
```

## Usage in SCENE

```python
SCENE = {
    "name": "default",
    "modules": [
        {"name": "hand", "module": "asimov.modules.hand", "config": {"enabled": True}},
    ],
    "conf": {
        "HAND": {
            "MAX_HANDS": 1,
            "DETECTION_CON": 0.8,
            "USE_OVERLAY": True,
        },
    },
}
```

## Dependencies

- cv2 (OpenCV)
- cvzone.HandTrackingModule.HandDetector
- asimov.conf
- asimov.common.ThreadSafeContext
- numpy
- time (stdlib)
