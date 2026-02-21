# glcvspinvideosmoothtwist Specification

## Overview

OpenGL video player that displays a video with smooth position/rotation animation. The video bounces off screen borders with continuous motion.

## Dependencies

- `cv2` - Video capture
- `numpy` - Array operations
- `glfw` - Window management
- `OpenGL.GL` - Rendering
- `asimov.util` - Utility functions

## Imports from asimov.util

```python
from asimov.util import (
    create_texture,
    update_texture,
    lerp,
    smooth_step,
    stable_phase,
)
```

## Functionality

### Video Capture
- Opens video source (default: webcam `1`)
- Loops video when reaching end

### Animation System

**State:**
```python
{
    'x': float,       # X position
    'y': float,       # Y position
    'z': float,       # Z position (depth)
    'angle': float,   # Rotation angle in degrees
    'vel_x': float,   # X velocity
    'vel_y': float,   # Y velocity
    'vel_z': float,   # Z velocity
    'vel_angle': float,  # Angular velocity
    'x_range': tuple, # (min, max) X bounds
    'y_range': tuple, # (min, max) Y bounds
    'z_range': tuple, # (min, max) Z bounds
    'angle_range': tuple, # (min, max) angle bounds
}
```

**anim_update(state):**
- Updates position based on velocity
- Bounces when quad edge hits border (not center)
- Reverses velocity direction at boundaries

### Rendering

1. Read video frame
2. Flip vertically for OpenGL texture coords
3. Upload to GPU texture via `update_texture()`
4. Calculate rotation from angle
5. Apply rotation to quad vertices
6. Translate quad by x, y, z offset
7. Render with shader program

### Controls

- **ESC**: Exit application

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| video_path | 1 | Video source (int for webcam, str for file) |
| window_size | 800x600 | OpenGL window dimensions |
| x_range | (-0.9, 0.9) | X movement bounds |
| y_range | (-0.9, 0.9) | Y movement bounds |
| angle_range | (-15, 15) | Rotation angle bounds |
| vel_x | 0.005 | X velocity per frame |
| vel_y | 0.005 | Y velocity per frame |
| vel_angle | 0.1 | Angular velocity per frame |

## Shaders

### Vertex Shader
- Pass through position and texture coordinates

### Fragment Shader
- Sample video texture and output to screen

## Notes

- Uses GL_TEXTURE_2D for video frame
- Texture coordinates: (0,0) bottom-left to (1,1) top-right
- Quad rotates around center point
- Movement bounds account for quad half-size (0.5)
