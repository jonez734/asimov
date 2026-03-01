# asimov-base Specification

## Overview

`asimov-base` is the core configuration and utilities package for Asimov. It provides shared configuration constants, base classes, and common utilities used across all other Asimov packages.

## Package Structure

```
asimov_base/
├── __init__.py      # Public API exports
├── conf.py          # Configuration constants
├── module.py        # Module loading and lifecycle management
├── util.py          # Shared utility functions
├── common.py        # Common base classes
├── scene.py         # Scene management
├── render.py        # Rendering utilities
├── render_opengl.py # OpenGL rendering
├── input.py         # Input handling
├── touch.py         # Touch detection
├── eyes.py          # Eye detection utilities
├── fingertip.py     # Fingertip utilities
├── cap.py           # Video capture utilities
├── lib.py           # Library utilities
├── menu.py          # Menu system
├── interactive_grid.py # Interactive grid utilities
├── __main__.py      # CLI entry point
└── main_*.py        # Various main entry points
```

## Module Specifications

### conf.py

Core configuration constants:

| Constant | Type | Default | Description |
|----------|------|---------|-------------|
| `LOGGER_NAME` | str | "asimov" | Logger name |
| `WINDOW_NAME` | str | "Asimov Preview" | Window title |
| `CAPTURE_DEVICE` | int | 0 | Camera device index |
| `CAPTURE_WIDTH` | int | 640 | Frame width |
| `CAPTURE_HEIGHT` | int | 480 | Frame height |
| `CAPTURE_FPS` | int | 30 | Frames per second |

### module.py

Module lifecycle and loading utilities:

**Classes:**
- `SignatureError` - Dataclass for signature mismatch errors

**Functions:**

| Function | Signature | Description |
|----------|-----------|-------------|
| `get` | `(module_input, args=None) -> ModuleType` | Resolve module reference (string or module object) |
| `load` | `(args, modulepath) -> ModuleType` | Load module from string path |
| `check` | `(args, mod_ref, **kwargs) -> bool` | Validate module interface and access |
| `run` | `(args, mod_ref, **kwargs)` | Execute module lifecycle: check -> init -> buildargs -> main |
| `runcallback` | `(args, callback, optional=False, **kwargs)` | Execute callback (string path or callable) |
| `check_func` | `(mod_ref, func_name, required_signature, allow_extra=True, enforce_return=True, silent=False) -> bool` | Validate function signature |

**Module Lifecycle:**
Each module must implement these functions:
- `init(args, **kwargs) -> bool` - Initialize module
- `access(args, op, **kwargs) -> bool` - Check operation access
- `buildargs(args, **kwargs) -> ArgumentParser` - Build argument parser
- `main(args, **kwargs) -> bool` - Main execution

### util.py

Shared utility functions:

**Constants:**
- `MAX_BLOCK_SIZE` = 128 - Maximum block size for frame encoding
- `LOGGER_NAME` = "asimov" - Logger name
- `FRAME_BLOCK_FORMAT` = "!HBBH" - Frame block struct format

**Classes:**
- `Block` - Dataclass for frame blocks (id, length, data)
- `OneEuroFilter` - One Euro Filter for smoothing

**Functions:**

| Function | Signature | Description |
|----------|-----------|-------------|
| `add_camera_args` | `(parser, hidden=False)` | Add camera capture arguments |
| `add_network_args` | `(parser, hidden=False)` | Add network transmission arguments |
| `render_text` | `(text, x, y, font=GLUT_BITMAP_8_BY_13, color=(0,1,0,1), shadow_color=(0,0,0,0.5), offsets=None, rect_color=None, rect_alpha=0.7)` | Render bitmap text with OpenGL |
| `render_quad` | `(texture_id)` | Render textured quad with OpenGL |
| `create_texture` | `() -> int` | Create OpenGL texture |
| `update_texture` | `(texture_id, frame)` | Upload frame as OpenGL texture |
| `encode_block` | `(block, compress=False) -> bytes` | Encode frame block |
| `decode_block` | `(data, block_size, channels=3) -> tuple[int, np.ndarray]` | Decode frame block |
| `block_id_to_xy` | `(block_id, frame_width, block_size) -> tuple[int, int]` | Convert block ID to pixel coordinates |
| `find_best_power_of_two_block_size` | `(h, w) -> int` | Find optimal power-of-two block size |
| `get_changed_blocks` | `(frame, previous_frame, frame_id, compress=True) -> List[Block]` | Detect changed blocks between frames |
| `calculate_total_blocks_in_frame` | `(frame_width, frame_height, block_size) -> int` | Calculate total blocks in frame |
| `draw_text` | `(img, x, y, text, color=(255,255,255), alpha=1.0, shadow_offset=1, shadow_color=(128,128,128), shadow_alpha=1.0, thickness=1, font_scale=0.5, font=cv2.FONT_HERSHEY_SIMPLEX, rect_color=None, rect_alpha=0.7) -> np.ndarray` | Draw text on cv2 frame |
| `get_bottom_right_position` | `(frame, text, font, font_scale=1.0, thickness=2, padding=10) -> tuple[int, int]` | Calculate text position for bottom-right |
| `get_device_by_label` | `(label) -> Optional[str]` | Find video device by label |
| `heading` | `(title, level=1, **kwargs)` | Print formatted heading |
| `get_centroid` | `(pts) -> tuple[float, float]` | Calculate centroid of contour/points |
| `blend_alpha` | `(foreground_bgr, background_bgr, alpha_channel) -> np.ndarray` | Blend foreground on background |
| `safe_bgra_draw` | `(canvas_bgra, draw_func, *args, **kwargs) -> np.ndarray` | Safely draw on BGRA canvas |
| `apply_layer_fade` | `(canvas, decay_rate) -> np.ndarray` | Apply temporal decay to layer |
| `interpolate_sequential` | `(index, total_length, start_value, end_value) -> float` | Interpolate values across sequence |
| `draw_diagnostics_overlay` | `(frame, diagnostics)` | Draw diagnostics on GL frame |
| `stable_phase` | `(seed, hash_base=31, scramble_shift1=16, scramble_shift2=3) -> float` | Generate stable phase from seed |
| `floating_bounce` | `(seed, amplitude=0.05, frequency=1.0, time=0.0) -> float` | Compute floating offset |
| `configure_capture` | `(cap, width=None, height=None, fps=None) -> Optional[tuple[int, int, int]]` | Configure video capture |

### common.py

Common base classes (see source for details)

### scene.py, render.py, render_opengl.py

Rendering and scene management (see source for details)

### input.py, touch.py, eyes.py, fingertip.py

Input handling and detection utilities (see source for details)

### cap.py

Video capture utilities (see source for details)

## Usage Examples

### Loading and Running a Module

```python
from asimov.base import module

# Load module by name
m = module.load(args, "asimov_modules.hand")

# Check module validity
if module.check(args, m):
    module.run(args, m)
```

### Using Utilities

```python
from asimov.base import util

# Add camera arguments to parser
parser = argparse.ArgumentParser()
util.add_camera_args(parser)

# Detect changed blocks
changed = util.get_changed_blocks(frame, prev_frame, frame_id=1)

# Use One Euro Filter
filter = util.OneEuroFilter(freq=30, min_cutoff=1.0, beta=0.01)
smoothed_value = filter.update(raw_value)
```
