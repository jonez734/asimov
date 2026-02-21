# rect Module Specification

## Overview

`rect` is an Asimov module that manages rectangles and renders them with touch highlighting. It provides default test rectangles and draws them on the frame, using touch state from the `rect_touch` module to determine colors.

## Architecture

- **detect()**: Creates default rectangles if none exist in context
- **draw()**: Reads rectangles and touch state from context, draws rectangles with highlighting

## Context Keys

| Key | Type | Description |
|-----|------|-------------|
| `rects` | List[Dict] | List of rectangle definitions |
| `rect_touches` | List[str] | List of touched rectangle IDs (from rect_touch module) |

## Rectangle Definition

```python
{
    "id": str,      # Rectangle identifier
    "x": int,       # X position
    "y": int,       # Y position  
    "w": int,       # Width
    "h": int,       # Height
}
```

## Dependencies

- Consumes: `context["rect_touches"]` - list of touched rectangle IDs
- Produces: `context["rects"]` - list of rectangle definitions

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| DRAW.enabled | bool | True | Draw rectangles |
| DRAW.COLOR | color | [0, 180, 255] | Rectangle color (BGR) |
| DRAW.TOUCHED_COLOR | color | [0, 0, 255] | Touched rectangle color (BGR) |
| DRAW.THICKNESS | int | 2 | Border thickness |
| DRAW.TOUCHED_THICKNESS | int | 3 | Touched border thickness |
| DRAW.LABEL_SCALE | float | 0.5 | Label font scale |
| DRAW.LABEL_THICKNESS | int | 1 | Label font thickness |

## Functions

### detect(frame, context)

Creates default test rectangles if none exist:
- `test1`: (100, 100, 100, 100)
- `test2`: (300, 100, 100, 100)
- `test3`: (500, 100, 100, 100)

### draw(frame, context) -> np.ndarray

Draws rectangles:
- Reads `rects` from context
- Reads `rect_touches` to determine which rectangles are touched
- Draws rectangle borders with color/thickness based on touch state
- Draws rectangle ID labels

## Module API

Asimov modules must implement draw() and detect(). ui_schema() is optional for dashboard UI.

```python
def detect(frame, context): ...     # Required
def draw(frame, context) -> np.ndarray: ...  # Required
def ui_schema(args=None, context=None) -> dict: ...  # Optional

# Optional lifecycle hooks:
def init(args, **kwargs) -> bool: ...
def buildargs(args, **kwargs): ...
def access(args, op, **kwargs) -> bool: ...
def main(args, **kwargs) -> bool: ...
```
