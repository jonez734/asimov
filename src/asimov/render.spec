# asimov.render Specification

## Overview

`render.py` provides OpenGL rendering utilities for Asimov, including shader compilation, texture loading, and geometry creation.

## Functions

### Texture Management

```python
def load_texture(image_path: str) -> int:
    """Load an image file as an OpenGL 2D texture."""
```

Loads a PNG/JPG image using PIL, flips it vertically for OpenGL coordinates, and creates an OpenGL texture with mipmap filtering.

Parameters:
- `image_path`: Path to the image file

Returns: OpenGL texture ID

### Shader Compilation

```python
def create_shader(vertex_source: str, fragment_source: str):
    """Compile vertex and fragment shaders and link into a program."""
```

Compiles GLSL shaders and links them into a shader program.

Parameters:
- `vertex_source`: GLSL vertex shader source code
- `fragment_source`: GLSL fragment shader source code

Returns: Compiled shader program handle

### Geometry

```python
def create_cube() -> tuple[int, int]:
    """Create a cube VAO with position and texture coordinates."""
```

Creates a cube with position (vec3) and texture coordinate (vec2) attributes. The cube has thickness 0.2 (-0.1 to +0.1 on Y axis).

Returns: Tuple of (VAO handle, index count)

## Shader Sources

```python
VERTEX_SHADER: str
FRAGMENT_SHADER: str
```

Default GLSL 3.30 core profile shaders for textured geometry with model/projection matrices.
