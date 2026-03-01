# face Module Specification

## Overview

`face` is an Asimov module that detects faces using MediaPipe FaceMesh. It publishes raw face landmarks into context for use by other modules like eyes_next.

## Architecture

- **detect()**: Runs FaceMesh detection on frame
- **draw()**: No-op (other modules consume face data)

## Context Keys

| Key | Type | Description |
|-----|------|-------------|
| `FACE` | dict | Face detection results with landmarks |

## Dependencies

- Produces: `context["FACE"]` - face landmarks data

## FACE Context Format

```python
context["FACE"] = {
    "detector": FaceMeshDetector,  # cvzone FaceMesh detector
    "faces": [...],               # List of detected faces
}
```

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| MESH.MAX_FACES | int | 2 | Max faces to detect |
| MESH.DETECTION_CON | float | 0.5 | Detection confidence |
| MESH.MIN_TRACK_CON | float | 0.5 | Tracking confidence |

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
