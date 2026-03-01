# fps_overlay Module Specification

## Overview

`fps_overlay` is an Asimov module that displays FPS (frames per second) metrics from the main_dashboard threads. It reads FPS values from the shared context and renders them as text overlays on the frame.

## Architecture

- **detect()**: Not implemented (this module only draws)
- **draw()**: Reads FPS from `context["FPS"]` and renders using `draw_text()`

## FPS Data Source

The module reads from `context["FPS"]` which is populated by main_dashboard:

```python
context["FPS"] = {
    "logic": fps_value,   # Detection thread FPS
    "render": fps_value,  # Render/display thread FPS
}
```

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| DRAW.enabled | bool | True | Show FPS overlay |
| DRAW.pos | tuple | (10, 80) | Text position (x, y) |
| DRAW.bg_color | color | [255, 0, 255] | Background color (BGR) |
| DRAW.text_color | color | [255, 255, 255] | Text color (BGR) |
| DRAW.scale | float | 1.0 | Text scale factor |
| DRAW.thickness | int | 2 | Text thickness |

## Display

The module displays two lines:
- `Logic FPS: XX` - FPS of the detection/processing thread
- `Render FPS: XX` - FPS of the render/display thread

Position defaults to (10, 80) to avoid overlapping with handedness labels at (10, 30).

## Dependencies

- cvzone (for putTextRect)
- numpy
- opencv-python
