# Asimov

Asimov is a real-time computer vision library for video processing, detection, and visualization. It provides modules for hand tracking, finger detection, playing card recognition, and more, with support for multiple rendering backends and network frame transmission.

## Features

- **Hand & Finger Detection** - MediaPipe-based hand tracking with fingertip detection
- **Face & Eyes Detection** - Facial landmark and eye tracking
- **Playing Card Recognition** - Detect and identify playing cards
- **Rectangle & Touch Detection** - Detect rectangular regions and touch interactions
- **Visual Effects** - Glitch effects, motion blur, FPS overlays
- **Multiple Rendering Backends** - OpenGL, imshow, virtual camera support
- **Network Frame Transmission** - UDP/TCP frame sending and receiving with chunking
- **Terminal I/O** - Rich terminal UI via bbsengine6

## Installation

```bash
pip install asimov
```

## Dependencies

- cvzone >= 1.5.6
- mediapipe >= 0.8.9
- numpy >= 1.21.0
- opencv-python >= 4.5.0
- pyvirtualcam >= 0.10.0

## Quick Start

```python
import cv2
from asimov import lib, conf

# Use the main dashboard application
lib.runmodule(args, "main_dashboard")
```

## Architecture

```
asimov/
├── __init__.py           # Package entry
├── __main__.py           # CLI entry point
├── conf.py               # Central configuration
├── lib.py                # Core library functions
├── common.py             # Common utilities
├── util.py               # General utilities
├── module.py             # Base module class
│
├── net/                  # Network transmission
│   ├── conf.py           # Network configuration
│   ├── socket.py         # Socket helpers
│   ├── packet.py         # Packet encoding/decoding
│   ├── tcp.py            # TCP sender/receiver
│   ├── udp.py           # UDP sender/receiver
│   └── ping.py          # Ping/pong utilities
│
├── io/                   # Terminal I/O
│   ├── echo.py           # Rich terminal output
│   ├── input.py          # Terminal input
│   ├── terminal.py       # Terminal utilities
│   └── ...
│
├── modules/              # Detection/processing modules
│   ├── hand.py           # Hand detection
│   ├── indexfingertip.py # Fingertip detection
│   ├── face.py           # Face detection
│   ├── eyes_next.py      # Eyes tracking
│   ├── rect.py           # Rectangle detection
│   ├── rect_touch.py     # Touch detection
│   ├── glitch.py         # Glitch effects
│   ├── motionblur.py     # Motion blur
│   ├── fps_overlay.py    # FPS display
│   └── float_playingcard.py # Card detection
│
├── playingcard/          # Playing card utilities
├── scene.py              # Scene management
├── render.py             # OpenGL rendering
├── render_opengl.py      # OpenGL backend
├── render_imshow.py      # imshow backend
├── videocapture.py       # Video capture
└── main_*.py             # Various entry points
```

## Configuration

Configuration is centralized in `asimov/conf.py`. All configs are stored in a unified `CONF` dict with nested sections.

### Thread-Safe Access (Recommended)

Use the built-in getters for thread-safe access:

```python
from asimov import conf

# Capture settings via CONF dict
conf.CONF["CAPTURE"]["DEVICE"]
conf.CONF["CAPTURE"]["WIDTH"]
conf.CONF["CAPTURE"]["HEIGHT"]
conf.CONF["CAPTURE"]["FPS"]

# Module configs via CONF dict
conf.CONF["HAND"]["ENABLED"]
conf.CONF["INDEXFINGERTIP"]["DETECTION"]["DETECTION_CON"]

# Or use thread-safe getters
conf.get("HAND")
conf.get_module("HAND")
conf.get_capture("DEVICE")
```

### Backward Compatibility

For backward compatibility, module-level aliases are available (NOT thread-safe):

```python
from asimov import conf

# Capture settings
conf.CAPTURE_DEVICE  # Camera device index
conf.CAPTURE_WIDTH   # Frame width
conf.CAPTURE_HEIGHT  # Frame height
conf.CAPTURE_FPS    # Frames per second

# Module configs
conf.HAND["ENABLED"]
conf.INDEXFINGERTIP["DETECTION"]["DETECTION_CON"]
```

### Thread-Safe Getters

| Function | Description |
|----------|-------------|
| `conf.get(key)` | Generic getter, returns deep copy |
| `conf.get_module(key)` | Get module config by name |
| `conf.get_capture(key)` | Get capture setting (DEVICE, WIDTH, etc.) |
| `conf.set_module(key, value)` | Set entire module config |
| `conf.update_module(key, updates)` | Partial update module config |

## External Configuration

Asimov supports loading configuration from an external JSON file for easier customization without editing source code.

### Using External Config

Set the `ASIMOV_CONFIG` environment variable to the path of your config file:

```bash
export ASIMOV_CONFIG=/path/to/config.json
```

If not set, Asimov defaults to `~/.asimov/config.json`.

### Verbose Logging

When an external config is loaded, Asimov logs details about the configuration:

```
asimov.conf INFO Loading external config from: /home/user/.asimov/config.json
asimov.conf INFO Config source: ~/.asimov/config.json (default)
asimov.conf INFO Loaded keys: ['HAND', 'OVERLAYS']
asimov.conf INFO Overridden CONF['HAND']: ['ENABLED', 'MODEL_COMPLEXITY']
asimov.conf INFO Overridden CONF['OVERLAYS']: ['hand', 'indexfingertip']
```

Enable debug logging for missing config file messages:

```python
logging.getLogger("asimov.conf").setLevel(logging.DEBUG)
```

### Partial Override

The external config does a **partial override** — only keys present in the JSON file are changed. All other values remain as defaults defined in `conf.py`.

### Example Config

See `config.example.json` in the asimov source for a complete reference of overridable keys:

```json
{
    "HAND": {
        "ENABLED": false
    },
    "OVERLAYS": {
        "hand": {
            "enabled": false,
            "order": 15
        }
    }
}
```

## Network (asimov.net)

Asimov provides UDP/TCP frame transmission for distributed video processing:

### UDP Sender

```python
from asimov.net import UDPSender
from asimov import util
import cv2

sender = UDPSender("127.0.0.1", 5000)
cap = cv2.VideoCapture(0)

result = util.configure_capture(cap, width=640, height=480, fps=30)
if result is None:
    exit(1)

frame_id = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break
    sender.send_frame(frame, frame_id, block_size=64, compress=False)
    frame_id += 1

sender.close()
```

### UDP Receiver

```python
from asimov.net import UDPReceiver
import cv2

receiver = UDPReceiver("0.0.0.0", 5000, blocking=False, timeout=1.0)

while True:
    result = receiver.receive()
    if result is None:
        continue
    if hasattr(result, 'frame_id'):
        cv2.imshow("Received", result)
        if cv2.waitKey(1) == ord('q'):
            break

receiver.close()
```

See `asimov/net.spec` for full API documentation.

## Modules

Asimov modules follow a standard interface with lifecycle and processing functions:

### Required Functions

```python
def init(args, **kwargs):
    """Initialize module resources."""

def access(args, op, /, **kwargs) -> bool:
    """Access control - return True if operation is allowed."""

def buildargs(args, **kwargs) -> argparse.ArgumentParser:
    """Build CLI arguments for this module."""

def detect(frame, context, **kwargs):
    """Process frame and update context with detection results."""

def draw(frame, context, **kwargs) -> np.ndarray:
    """Draw overlays on frame. Returns modified frame."""

def main(args, **kwargs) -> bool:
    """Standalone execution if module is run directly."""
```

### Optional Functions

```python
def ui_schema(args=None, context=None) -> dict:
    """Return UI schema for module configuration."""
```

### Available Modules

- **hand** - MediaPipe hand detection with landmark tracking
- **indexfingertip** - Detect and track index fingertip position
- **face** - Face detection with MediaPipe
- **eyes_next** - Eye tracking with gaze detection
- **rect** - Detect rectangular regions in frame
- **rect_touch** - Detect touch interactions with rectangles
- **glitch** - Visual glitch effects (VHS warp, datamosh, ghosting)
- **motionblur** - Motion blur effect
- **fps_overlay** - Display FPS counter on frame
- **float_playingcard** - Detect and identify playing cards

## Rendering

### OpenGL Rendering

```python
from asimov.render import create_texture, update_texture, render_quad
from asimov import render_opengl
```

### imshow Rendering

```python
from asimov import render_imshow
```

### Virtual Camera

```python
import pyvirtualcam
with pyvirtualcam.Camera(width=640, height=480, fps=30) as cam:
    cam.send(frame)  # Send frame to virtual camera
```

## Terminal I/O

Asimov uses bbsengine6 for terminal I/O:

```python
from bbsengine6 import io

io.echo("Hello {bold}world{/bold}!")
io.echo("{red}Error{/red} message")
io.echo("{green}Success{/green}")
```

## Demos

Several demo scripts are available in the project root:

```bash
# Network transmission demos (asimov.net)
python demo_net_send_frame.py
python demo_net_receive_frame.py
python demo_net_udp_sender.py
python demo_net_udp_receiver.py
python demo_net_tcp_pingpong.py

# Detection demos
python demo_float_playingcard.py
python demo_fingertip_detect_rank_suit.py

# Virtual camera
python demo_pyvirtualcam.py

# Main applications
python -m asimov
```

## CLI Options

```bash
python -m asimov --help

Options:
  --verbose              Enable verbose output
  --debug               Enable debug mode
  --basedir PATH        Base directory for data files
  --set-name NAME       Card set name (default: bicycle)
  --capture-device NUM  Camera device index
  --capture-width NUM   Frame width
  --capture-height NUM  Frame height
  --capture-fps NUM     Capture FPS
```

## Development

### Running Tests

```bash
# Import test
python -c "import asimov; print('OK')"
```

### Code Structure

- `asimov/conf.py` - All configuration constants (ABI-stable)
- `asimov/*.spec` - Module specifications
- `asimov/io/` - Terminal I/O utilities
- `asimov/modules/` - Detection/processing modules
- `asimov/net/` - Network transmission

## License

MIT
