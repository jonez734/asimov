# motionblur Module Specification

## Overview

`motionblur` is an Asimov module that creates a motion blur trail effect following the index fingertip. It maintains a history of recent fingertip positions and blends them.

## Architecture

- **detect()**: Tracks fingertip position, maintains position history
- **draw()**: Renders motion blur trail by blending recent positions

## Context Keys

| Key | Type | Description |
|-----|------|-------------|
| `MOTIONBLUR` | dict | Motion blur state |
| `INDEXFINGERTIP` | dict | Fingertip position (consumed) |

## Dependencies

- Consumes: `context["INDEXFINGERTIP"]` - fingertip position data
- Produces: `context["MOTIONBLUR"]` - motion blur state

## MOTIONBLUR Context Format

```python
context["MOTIONBLUR"] = {
    "frames": deque,       # History of recent positions
    "last_pos": (x, y),   # Last known position
    "active": bool,        # Whether effect is active
    "error_state": bool,
}
```

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| ENABLED | bool | True | Enable motion blur |
| HISTORY_LEN | int | 10 | Number of frames to blend |
| ALPHA | float | 0.85 | Blend opacity |
| MIN_VELOCITY | float | 5.0 | Min velocity to activate |
| MAX_TRAIL_LEN | int | 8 | Max trail length |

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
