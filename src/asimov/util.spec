# asimov.util Specification

## Overview

`util.py` provides utility functions for Asimov computer vision modules, including text rendering, OpenGL operations, image processing, and filtering.

## Constants

```python
MAX_BLOCK_SIZE = 128
LOGGER_NAME = "asimov"
FRAME_BLOCK_FORMAT = "!HBBH"
```

## Text Rendering

### OpenGL (render_text)

Renders bitmap text using OpenGL/GLUT for virtual display.

```python
def render_text(
    text: Optional[str],
    x: float,
    y: float,
    font: Any = GLUT_BITMAP_8_BY_13,
    color: Sequence[float] = (0.0, 1.0, 0.0, 1.0),
    shadow_color: Optional[Sequence[float]] = (0.0, 0.0, 0.0, 0.5),
    offsets: Optional[List[Tuple[float, float]]] = None,
) -> None:
```

Parameters:
- `text`: Text to render (None or empty = no-op)
- `x, y`: Position in normalized OpenGL coordinates (0-1)
- `font`: GLUT font constant
- `color`: RGBA color (values can be 0.0-1.0 or 0-255)
- `shadow_color`: Shadow RGBA color
- `offsets`: Custom shadow offset positions

### OpenCV (draw_text)

Renders text on cv2 frames with shadow and alpha blending.

```python
def draw_text(
    img: np.ndarray,
    x: int,
    y: int,
    text: str,
    color: Tuple[int, int, int] = (255, 255, 255),
    alpha: float = 1.0,
    shadow_offset: Union[int, Tuple[int, int]] = 1,
    shadow_color: Tuple[int, int, int] = (128, 128, 128),
    shadow_alpha: float = 1.0,
    thickness: int = 1,
    font_scale: float = 0.5,
    font: int = cv2.FONT_HERSHEY_SIMPLEX,
) -> np.ndarray:
```

Parameters:
- `img`: cv2 frame (BGR or BGRA)
- `x, y`: Pixel position
- `text`: Text string
- `color`: RGB color tuple
- `alpha`: Alpha blending factor (0-1)
- `shadow_offset`: Shadow offset (int or tuple)
- `shadow_color`: Shadow RGB color
- `shadow_alpha`: Shadow alpha
- `thickness`: Text thickness
- `font_scale`: Font scale
- `font`: OpenCV font constant

Returns: Modified cv2 frame

### Text Position

```python
def get_bottom_right_position(
    frame: np.ndarray,
    text: str,
    font: int,
    font_scale: float = 1.0,
    thickness: int = 2,
    padding: int = 10,
) -> Tuple[int, int]:
```

Calculate (x, y) position for text in lower-right corner.

## OpenGL Operations

```python
def create_texture() -> int:
    """Create and return an OpenGL texture ID."""

def update_texture(texture_id: int, frame: Optional[np.ndarray]) -> None:
    """Upload a BGR cv2 frame as an OpenGL texture."""

def render_quad(texture_id: int) -> None:
    """Render a textured quad filling the screen."""
```

## Image Processing

### Block Encoding/Decoding

```python
@dataclass
class Block:
    id: int
    length: int
    data: bytes

def encode_block(block: Block, compress: bool = False) -> bytes:
    """Encode a Block into binary format for network transmission."""

def decode_block(data: bytes, block_size: int, channels: int = 3) -> tuple[int, np.ndarray]:
    """Decode a block from bytes into a NumPy array."""

def block_id_to_xy(block_id: int, frame_width: int, block_size: int) -> Tuple[int, int]:
    """Convert block ID to pixel coordinates."""

def find_best_power_of_two_block_size(h: int, w: int) -> int:
    """Find largest power-of-two block size dividing both h and w."""

def get_changed_blocks(
    frame: np.ndarray,
    previous_frame: np.ndarray,
    frame_id: int,
    compress: bool = True,
) -> List[Block]:
    """Detect changed blocks between two frames."""

def calculate_total_blocks_in_frame(frame_width: int, frame_height: int, block_size: int) -> int:
    """Calculate total number of blocks in a frame."""
```

### Alpha Blending

```python
def blend_alpha(
    foreground_bgr: np.ndarray,
    background_bgr: np.ndarray,
    alpha_channel: np.ndarray,
) -> np.ndarray:
    """Blend foreground onto background using alpha channel."""

def apply_layer_fade(canvas: np.ndarray, decay_rate: float) -> np.ndarray:
    """Apply temporal decay/fade-out to an image layer."""
```

### Contour Processing

```python
def get_centroid(pts: np.ndarray) -> Tuple[float, float]:
    """Calculate centroid of contour or points."""

def safe_bgra_draw(
    canvas_bgra: np.ndarray,
    draw_func: Callable[..., Any],
    *args,
    **kwargs,
) -> np.ndarray:
    """Safely execute OpenCV drawing on BGRA canvas."""
```

## Filtering

### One Euro Filter

```python
class OneEuroFilter:
    def __init__(
        self,
        freq: float = 30,
        min_cutoff: float = 1.0,
        beta: float = 0.01,
        dcutoff: float = 1.0,
        init: Optional[float] = None,
    ) -> None:
    
    def update(self, x: float) -> float:
        """Apply filter to new value and return smoothed result."""
```

Implements the One Euro Filter algorithm for smoothing values while maintaining responsiveness to quick movements.

### Phase Functions

```python
def stable_phase(
    seed: Any,
    hash_base: int = 31,
    scramble_shift1: int = 16,
    scramble_shift2: int = 3,
) -> float:
    """Generate stable [0, 2π) phase offset from hashable seed."""

def floating_bounce(
    seed: Any,
    amplitude: float = 0.05,
    frequency: float = 1.0,
    time: float = 0.0,
) -> float:
    """Compute floating offset using stable phase."""
```

### Interpolation

```python
def interpolate_sequential(
    index: int,
    total_length: int,
    start_value: float,
    end_value: float,
) -> float:
    """Map sequential index to proportional value between endpoints."""
```

## Diagnostics

```python
def draw_diagnostics_overlay(frame: np.ndarray, diagnostics: Dict[str, float]) -> None:
    """Draw diagnostics overlay on GL frame."""
```

## Device Utilities

```python
def get_device_by_label(label: str) -> Optional[str]:
    """Find V4L device by label (e.g., "PyVirtualCam")."""
```

## Terminal UI

```python
def heading(title: str, level: int = 1, **kwargs) -> None:
    """Print a terminal UI heading/box."""
```

## Internal Helpers

```python
def _normalize_color(c: Sequence[float]) -> Tuple[float, float, float, float]:
    """Normalize color tuple to 0.0-1.0 range."""

def _get_shadow_offsets(
    offsets: Optional[List[Tuple[float, float]]] = None,
) -> List[Tuple[float, float]]:
    """Get default or custom shadow offsets."""
```
