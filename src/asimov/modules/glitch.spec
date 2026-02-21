# glitch Module Specification

## Overview

`glitch` is an Asimov module that applies visual glitch effects to the frame. It randomly triggers various glitch effects like VHS warp, datamosh, ghosting, scanlines, and more.

## Architecture

- **detect()**: Manages glitch timing and triggers effects
- **draw()**: Applies glitch effects to frame

## Glitch Effects

The module supports multiple glitch effects:
- `vhs_warp` - VHS tracking warp effect
- `datamosh` - Datamosh/hybrid image glitch
- `ghost` - Frame ghosting with alpha blending
- `scanlines` - CRT scanline overlay
- `whitenoise` - White noise overlay
- `tearing` - Horizontal tearing
- `color_shift` - RGB channel offset
- `vertical_hold` - Vertical hold instability

## Dependencies

- Applies effects directly to frame (no context dependencies)

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| ENABLED | bool | True | Enable glitch module |
| MIN_INTERVAL | float | 2.0 | Min seconds between glitches |
| MAX_INTERVAL | float | 6.0 | Max seconds between glitches |
| MIN_DURATION | float | 0.5 | Min glitch duration |
| MAX_DURATION | float | 2.5 | Max glitch duration |
| MAX_CONCURRENT | int | 2 | Max concurrent effects |
| REGISTRY.<effect>.enabled | bool | True | Enable specific effect |
| REGISTRY.<effect>.weight | float | varies | Effect probability weight |

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
