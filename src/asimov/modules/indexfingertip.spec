# indexfingertip Module Specification

## Overview

`indexfingertip` is an Asimov module that tracks the index fingertip position when the index finger is raised. It uses One Euro Filter for smoothing.

## Architecture

- **detect()**: Detects hand, checks if index finger is up, extracts fingertip position
- **draw()**: Draws fingertip pointer on frame

## Context Keys

| Key | Type | Description |
|-----|------|-------------|
| `HAND` | dict | Hand detection results from hand module |
| `INDEXFINGERTIP` | dict | Fingertip tracking data |

## Detection Logic

1. Consumes hand data from `context["HAND"]`
2. Uses cvzone's `fingersUp()` to check finger state
3. Only activates when index finger pattern matches: `[0, 1, 0, 0, 0]`
4. Extracts landmark 8 (index fingertip) position
5. Applies One Euro Filter smoothing

## Dependencies

- Consumes: `context["HAND"]` - hand detection data with cvzone detector
- Produces: `context["INDEXFINGERTIP"]` - fingertip position data

## INDEXFINGERTIP Context Format

```python
context["INDEXFINGERTIP"] = {
    "active": bool,           # Whether fingertip is detected
    "data": {
        "x": float,          # Smoothed X position
        "y": float,          # Smoothed Y position
        "timestamp": float,  # Detection timestamp
    },
    "error_state": bool,
    "ema": {...}             # OneEuroFilter instances
}
```

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| DETECTION_CON | float | 0.6 | Detection confidence threshold |
| FILTER.enabled | bool | True | Enable filtering |
| FILTER.alpha | float | 0.4 | Smoothing factor |
| FILTER.deadzone | int | 2 | Deadzone in pixels |
| FILTER.FREQ | float | 30.0 | Filter frequency (Hz) |
| FILTER.MIN_CUTOFF | float | 1.0 | Min cutoff |
| FILTER.BETA | float | 0.0 | Speed coefficient |
| DRAW.enabled | bool | True | Draw pointer |
| DRAW.radius | int | 6 | Pointer radius |
| DRAW.color | color | [0, 255, 0] | Pointer color (BGR) |
| DRAW.thickness | int | -1 | Thickness (-1=filled) |

## Module API

Asimov modules loaded via `asimov.module` must implement these lifecycle functions:

```python
def detect(frame, context): ...     # Required
def draw(frame, context) -> np.ndarray: ...  # Required
def init(args, **kwargs) -> bool: ...        # Required
def buildargs(args, **kwargs): ...            # Required
def access(args, op, **kwargs) -> bool: ...  # Required
def main(args, **kwargs) -> bool: ...         # Required

def ui_schema(args=None, context=None) -> dict: ...  # Optional
```
