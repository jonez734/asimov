# rect_touch Module Specification

## Overview

`rect_touch` is an Asimov module that detects when the index fingertip is touching a rectangle. It reads rectangle definitions from context and writes touched rectangle IDs to context.

## Architecture

- **detect()**: Checks if fingertip is inside any rectangle
- **draw()**: No-op (rendering handled by rect module)

## Context Keys

| Key | Type | Description |
|-----|------|-------------|
| `rects` | List[Dict] | List of rectangle definitions (from rect module) |
| `rect_touches` | List[str] | Output: list of touched rectangle IDs |

## Detection Logic

Uses simple point-in-rectangle test:
```
rx <= x <= rx + rw  AND  ry <= y <= ry + rh
```

Where `(x, y)` is the fingertip position and `(rx, ry, rw, rh)` defines the rectangle.

## Dependencies

- Consumes: 
  - `context["rects"]` - list of rectangle definitions
  - `context["INDEXFINGERTIP"]` - fingertip position from indexfingertip module
- Produces: `context["rect_touches"]` - list of touched rectangle IDs

## INDEXFINGERTIP Context Format

```python
context["INDEXFINGERTIP"] = {
    "active": bool,
    "data": {
        "x": float,      # X position
        "y": float,      # Y position
        "timestamp": float,
    },
    ...
}
```

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| DETECTION.enabled | bool | True | Enable touch detection |

## Functions

### detect(frame, context)

1. Get rectangles from `context["rects"]`
2. Get fingertip position from `context["INDEXFINGERTIP"]`
3. For each rectangle, test if fingertip is inside
4. Write list of touched rectangle IDs to `context["rect_touches"]`

### draw(frame, context) -> np.ndarray

No-op. Returns frame unchanged.

## Module API

```python
def detect(frame, context): ...
def draw(frame, context) -> np.ndarray: ...
def ui_schema(args=None, context=None) -> dict: ...
def init(args, **kwargs) -> bool: ...
def main(args, **kwargs) -> bool: ...
```

## Notes

- Touch detection requires INDEXFINGERTIP module to be active with valid data
- Rectangle definitions must exist in context before detection works
- The rect module is responsible for creating/managing rectangles
- This module only detects touches - rendering is done by rect module
