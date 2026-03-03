# eyes_next Module Specification

## Overview

`eyes_next` is an Asimov module that detects eyes from face landmarks and draws a privacy bar over them. It smooths the bar position using One Euro Filter.

## Architecture

- **detect()**: Processes face landmarks to find eye positions
- **draw()**: Draws rotated privacy bar over eyes

## Context Keys

| Key | Type | Description |
|-----|------|-------------|
| `FACE` | dict | Face detection results from face module |
| `EYES` | dict | Eye tracking data with smoothed position |

## REQUIRES / PROVIDES

- REQUIRES: `FACE`
- PROVIDES: `EYES`

## Dependencies

- Consumes: `context["FACE"]` - face detection data
- Produces: `context["EYES"]` - eye position and bar geometry

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| FILTER.FREQ | float | 60.0 | Filter frequency (Hz) |
| FILTER.MIN_CUTOFF | float | 1.0 | Min cutoff |
| FILTER.BETA | float | 0.01 | Responsiveness |
| BAR.WIDTH_SCALE | float | 1.6 | Bar width relative to eye bbox |
| BAR.HEIGHT_SCALE | float | 2.2 | Bar height relative to eye bbox |
| BAR.COLOR | color | [0, 0, 0] | Bar color (BGR) |
| BAR.ALPHA | float | 0.85 | Bar opacity |
| BAR.GRACE_PERIOD | float | 0.35 | Seconds to keep bar after detection loss |

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
