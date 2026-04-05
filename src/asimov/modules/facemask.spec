# facemask.spec

## Module Overview

**Module name:** facemask
**Type:** PNG image overlay on face
**Dependency:** FACE module (face landmarks)

## REQUIRES / PROVIDES

- REQUIRES: `FACE`
- PROVIDES: `FACEMASK`

Overlays a PNG image on a detected face, scaled to fit the face bounding box.

## Configuration (conf.py)

```python
FACEMASK = {
    "ENABLED": False,
    "IMAGE": {
        "IMAGE_PATH": "",
        "POSITION": "TL",
        "LANDMARK": 10,
    },
    "ADJUST": {
        "SCALE": 1.0,
        "OFFSET_X": 0,
        "OFFSET_Y": 0,
    },
}
```

## Context

### Input (from FACE module)
- `context["FACE"]["faces"]` - List of face landmark arrays

### Output
- `context["FACEMASK"]["faces"]` - List of dicts with face dimensions
- `context["FACEMASK"]["overlay_img"]` - Loaded PNG image
- `context["FACEMASK"]["timestamp"]` - Last detection time
- `context["FACEMASK"]["error_state"]` - Error flag

## Functions

### detect(frame, context, **kwargs)

Reads face landmarks from `context["FACE"]`, calculates face bounding boxes, stores in `context["FACEMASK"]`.

### draw(frame, context, **kwargs) -> np.ndarray

Overlays PNG image on each face. Image is scaled to cover the face bounding box.

### ui_schema(args=None, context=None) -> dict

Returns dashboard UI config:
- IMAGE.IMAGE_PATH: file (PNG files)
- IMAGE.POSITION: radio (TL, TC, TR, CENTER, default: TL)
- IMAGE.LANDMARK: int (0-467)
- ADJUST.SCAL E: float (0.1-3.0, default 1.0)
- ADJUST.OFFSET_X: int (-200 to 200, default 0)
- ADJUST.OFFSET_Y: int (-200 to 200, default 0)

## Position Options

- **TL** (top-left): Pinned to left edge and top of face bounding box
- **TC** (top-center): Pinned to top-center of face bounding box  
- **TR** (top-right): Pinned to right edge and top of face bounding box
- **CENTER**: Centered on face bounding box

All positions scale the PNG to cover the full face bounding box.

## Features

- Multiple face support (loops through all faces)
- PNG transparency support (alpha channel)
- Grace period to keep overlay visible when face lost
- Configurable scale factor for fine-tuning size
- Configurable X/Y offsets for positioning adjustment

## Integration

Add to pipeline after face module:
```python
from asimov.modules import face, facemask

modules = [face, facemask, ...]
```

Requires FACE module to be enabled.
