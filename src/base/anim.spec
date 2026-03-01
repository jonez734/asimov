# asimov.anim Specification

## Overview

Animation utilities for Asimov including interpolation, easing, rotation, and bounce physics.

## Interpolation

### lerp

```python
def lerp(start: float, end: float, t: float) -> float:
```

Linear interpolation between start and end by t (0-1).

### smooth_step

```python
def smooth_step(t: float) -> float:
```

Smoothstep easing function (cubic Hermite interpolation).

### ease_in_out

```python
def ease_in_out(t: float) -> float:
```

Ease-in-out cubic interpolation.

## Geometry

### rotate_vertex

```python
def rotate_vertex(x: float, y: float, angle_deg: float) -> Tuple[float, float]:
```

Rotate a 2D point around origin by angle in degrees.

Returns: (rotated_x, rotated_y)

## Bounce Animation

### create_bounce_state

```python
def create_bounce_state(
    x_range: Tuple[float, float] = (-0.9, 0.9),
    y_range: Tuple[float, float] = (-0.9, 0.9),
    z_range: Tuple[float, float] = (-0.3, 0.0),
    angle_range: Tuple[float, float] = (-15, 15),
    vel_x: float = 0.005,
    vel_y: float = 0.005,
    vel_z: float = 0.0,
    vel_angle: float = 0.1,
) -> Dict[str, Any]:
```

Create initial bounce animation state.

Returns state dict with:
- `x`, `y`, `z`, `angle`: current position/angle
- `vel_x`, `vel_y`, `vel_z`, `vel_angle`: velocities
- `x_range`, `y_range`, `z_range`, `angle_range`: bounds

### bounce_animation_update

```python
def bounce_animation_update(
    state: Dict[str, Any],
    quad_size: float = 0.5,
) -> Dict[str, float]:
```

Update bounce animation state.

Parameters:
- `state`: Animation state dict from `create_bounce_state()`
- `quad_size`: Half-size of the object (for edge collision)

Returns position dict with:
- `x`, `y`, `z`: position
- `angle`: rotation angle

## Usage Example

```python
from asimov.anim import create_bounce_state, bounce_animation_update, rotate_vertex

# Create animation state
state = create_bounce_state()

# In animation loop
anim = bounce_animation_update(state)
x, y = rotate_vertex(0.5, 0.5, anim['angle'])
```
