# glcvgreenrectaroundcard Specification

## Overview

OpenCV/OpenGL webcam application that detects rectangular contours (playing cards) and draws green rectangles around them with area labels.

## Dependencies

- `cv2` - Video capture and image processing
- `numpy` - Array operations
- `glfw` - Window management
- `OpenGL.GL` - Rendering
- `OpenGL.GLU` - Orthographic projection
- `OpenGL.GLUT` - Text rendering (bitmap fonts)

## Functionality

### Card Detection

1. Convert frame to grayscale
2. Apply Gaussian blur (5x5 kernel)
3. Run Canny edge detection (thresholds: 50, 150)
4. Find external contours
5. Approximate contours to polygons
6. Keep contours with 4 vertices (quadrilaterals)
7. Filter by minimum area (> 1000 pixels)

### Rectangle Buffer

- Stores detected rectangles with timestamp
- Each entry: `(x, y, w, h, timestamp)`
- Rectangles displayed for 2 seconds after detection

### Rendering

1. Set up orthographic projection (0 to width, 0 to height)
2. Update OpenGL texture with current frame
3. Draw video as textured quad
4. Draw green rectangles around detected cards
5. Display area text above each rectangle

### Controls

- **ESC**: Exit application

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| width | 640 | Window width |
| height | 480 | Window height |
| DISPLAY_TIME | 2.0 | Rectangle display duration (seconds) |
| min_area | 1000 | Minimum contour area to detect |
| canny_low | 50 | Canny edge detection low threshold |
| canny_high | 150 | Canny edge detection high threshold |
| epsilon_factor | 0.02 | Contour approximation epsilon |

## Command Line Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--capture-dev` | 1 | Capture device index (0 for default webcam, 1 for external) |

## Notes

- Uses legacy OpenGL (immediate mode)
- Webcam defaults to device index 1
- GLUT must be initialized for text rendering
- Enables blending for transparency support
