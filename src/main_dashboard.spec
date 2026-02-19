# main_dashboard Specification

## Overview

`main_dashboard` is an Asimov module runner with an integrated Tkinter dashboard UI. It loads detection/draw modules, runs detection in a background thread, renders to a virtual camera, and displays a combined preview + control panel in a single window.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Dashboard Window                         │
│  ┌─────────────────────┬───────────────────────────────────┐
│  │   Preview Canvas    │      Control Panel                │
│  │   (tk.Canvas)       │  ┌─────────────────────────────┐  │
│  │                     │  │ Module Enable Checkboxes     │  │
│  │   BGR → RGB        │  ├─────────────────────────────┤  │
│  │   PIL → PhotoImage │  │ Notebook Tabs               │  │
│  │                     │  │ (per-module ui_schema)      │  │
│  │                     │  ├─────────────────────────────┤  │
│  │                     │  │ Status Output Text         │  │
│  └─────────────────────┴──┴─────────────────────────────┴──┘
└─────────────────────────────────────────────────────────────┘
         ▲                          ▲
         │                          │
    cv2.VideoCapture           pyvirtualcam.Camera
         │                          │
         ▼                          │
┌─────────────────────┐             │
│  SHARED_FRAME      │─────────────┘
│  (ThreadSafeContext)
│         ▲
         │
┌────────┴────────┐
│ Logic Thread   │
│ (detect only)  │
└────────┬────────┘
         │
    Module.detect()
```

## Components

### 1. DashboardApp (Tkinter)

**Location:** `main_dashboard.py` class `DashboardApp`

**UI Layout:**
- **Left panel (60% width)**: Preview canvas (black background)
- **Right panel (40% width)**: Control area
  - Header: "Asimov Control Panel" + status label
  - Module checkboxes: Enable/disable each module
  - Notebook tabs: One tab per module, populated from `ui_schema()`
  - Status output: Text area for log messages
  - Buttons: Refresh Schema, Show Config, Stop

**Methods:**
- `__init__(root, modules)`: Initialize with module list
- `_build_ui()`: Construct Tkinter UI
- `_update_canvas()`: Periodic frame display (~30fps)
- `push_frame(frame)`: Called by render thread to update preview
- `_toggle_module(name, enabled)`: Toggle module enabled state
- `_build_module_tabs()`: Generate config UI from `ui_schema()`
- `_get_module_config(name)`: Map module name to conf object
- `_refresh_schema()`: Rebuild config tabs
- `_show_all_config()`: Dump all config to text area
- `_stop()`: Set running=False and quit

### 2. Frame Update Loop

- Runs via `root.after(33, self._update_canvas)` (~30fps)
- Gets frame from `self.current_frame` (set by `push_frame()`)
- Converts BGR→RGB, resizes to fit canvas, displays via `PhotoImage`
- Uses `canvas.create_image()` with CENTER anchor

### 3. Render Thread

- Target: `render_loop()` (daemon thread)
- Captures from `cv2.VideoCapture`
- Runs module `draw()` functions
- Flips frame horizontally
- Sends to virtual camera via `pyvirtualcam`
- Pushes copy to dashboard via `app.push_frame()`

### 4. Logic Thread

- Target: `_consumer(modules, args)`
- Runs module `detect()` functions
- Uses `logic_lock` to synchronize frame access
- Updates `context["SHARED_FRAME"]`

## Module Interface

Modules must implement:

```python
def detect(frame, context: ThreadSafeContext, **kwargs):
    """Run detection, publish to context."""
    pass

def draw(frame, context: ThreadSafeContext, **kwargs) -> np.ndarray:
    """Draw overlays on frame, return modified frame."""
    pass

def ui_schema(args=None, context=None) -> dict:
    """Return config schema for dashboard UI."""
    pass

def init(args, **kwargs) -> bool: ...
def access(args, op, **kwargs) -> bool: ...
def buildargs(args, **kwargs) -> argparse.ArgumentParser: ...
def main(args, **kwargs) -> bool: ...
```

## Configuration

Modules map to `conf` attributes:

| Module Name | Config Object |
|-------------|--------------|
| hand        | conf.HAND    |
| indexfingertip | conf.INDEXFINGERTIP |
| face        | conf.FACE    |
| eyes_next   | conf.EYES    |
| glitch      | conf.GLITCH  |
| motionblur  | conf.MOTIONBLUR |

## UI Schema Types

The dashboard supports these field types in `ui_schema()`:

| Type    | Widget        |
|---------|---------------|
| float   | Scale + Entry |
| int     | Scale + Entry |
| bool    | Checkbutton   |

Schema format:
```python
{
    "SECTION": {
        "KEY": {
            "type": "float|int|bool",
            "default": ...,
            "min": ...,
            "max": ...,
            "step": ...,
            "label": "Display Name"
        }
    }
}
```

## Runtime Behavior

1. **Startup**: Load modules from `conf.OVERLAYS`, run lifecycle (`init`, `buildargs`, `main`)
2. **Camera**: Open VideoCapture, query actual resolution/fps
3. **Threads**: Start logic thread, then render thread, then Tkinter mainloop
4. **Runtime**:
   - User toggles module checkboxes → enables/disables in `item["config"]`
   - User edits config fields → updates `conf.*` dicts in real-time
   - Logic thread reads updated config on next detect() call
5. **Shutdown**: ESC key or Stop button → `app.running = False` → threads exit

## Command Line

```bash
python -m asimov main_dashboard --capture-device 0 --capture-width 640 --capture-height 480 --capture-fps 30
```

Arguments (via `common` module):
- `--capture-device`: Camera index (default: 0)
- `--capture-width`: Frame width (default: 640)
- `--capture-height`: Frame height (default: 480)
- `--capture-fps`: Target FPS (default: 30)

## Dependencies

- `cv2` (OpenCV)
- `numpy`
- `pyvirtualcam`
- `tkinter` (stdlib)
- `PIL` (Pillow)

## Future Considerations

- Multi-camera support (multiple VideoCaptures, multiple outputs)
- Hotkey handling (currently unused - was in original main_generic)
- Module-specific status displays (e.g., hand detection count)
- Video recording/screenshot from preview
