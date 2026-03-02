# asimov Package Specification

## Overview

`asimov` is the top-level package for Asimov, a computer vision framework for real-time video processing, hand tracking, face detection, and network frame transmission. The package provides backward-compatible access to all subpackages.

## Package Structure

```
asimov/
├── __init__.py           # Package initialization, re-exports
├── common.py             # Re-exports from base.common
├── io/                   # Terminal I/O module
│   ├── __init__.py       # Public API exports
│   ├── echo.py           # Rich terminal output
│   ├── terminal.py       # Terminal utilities
│   ├── palette.py        # Color palettes
│   ├── getch.py          # Character input
│   ├── getstr.py         # String input
│   └── ...               # Other I/O utilities
├── base/                 # Core utilities
│   ├── __init__.py       # Public exports
│   ├── conf.py           # Configuration
│   ├── module.py         # Module lifecycle
│   ├── util.py           # Utilities
│   ├── common.py         # Common classes
│   └── ...               # Other base modules
├── net/                  # Networking (TCP/UDP)
│   ├── __init__.py       # Public exports
│   ├── conf.py           # Network config
│   ├── socket.py         # Socket utilities
│   ├── packet.py         # Packet encoding
│   ├── frame.py          # Frame encoding
│   ├── tcp.py            # TCP sender/receiver
│   ├── udp.py            # UDP sender/receiver
│   └── ping.py           # Ping/pong utilities
├── modules/              # CV modules
│   ├── __init__.py       # Public exports
│   ├── conf.py           # Module configuration
│   ├── hand.py           # Hand detection
│   ├── face.py           # Face detection
│   ├── indexfingertip.py # Fingertip detection
│   ├── rect.py           # Rectangle rendering
│   ├── rect_touch.py     # Touch detection
│   ├── eyes_next.py      # Eye privacy bars
│   ├── fps_overlay.py    # FPS display
│   ├── glitch.py         # Glitch effects
│   ├── motionblur.py     # Motion blur
│   ├── float_card.py     # Floating card
│   └── float_playingcard.py # Playing card
└── playingcard/          # Card detection
    ├── __init__.py       # Public exports
    └── asimov_playingcard/
        ├── __init__.py   # Card detection
        ├── cards.py      # Card structures
        ├── detect.py    # Detection logic
        ├── set.py       # Card sets
        ├── templates.py # Templates
        └── ...
```

## Public API

### Package Exports

The `asimov` package re-exports all subpackages for convenience:

```python
from asimov import base, io, net, modules, playingcard
```

### asimov.io

Terminal I/O with rich formatting:

| Item | Description |
|------|-------------|
| `echo` | Print formatted text with colors, cursor movement |
| `echo_traceback` | Print exception traceback |
| `rendered_length` | Calculate rendered text length |
| `get_cursor_position` | Get terminal cursor position |

See `asimov.io/SPEC.md` for full details.

### asimov.base

Core utilities and configuration:

| Item | Description |
|------|-------------|
| `conf` | Configuration constants (CAPTURE_DEVICE, WINDOW_NAME, etc.) |
| `module` | Module loading and lifecycle management |
| `util` | Utilities (OneEuroFilter, draw_text, etc.) |
| `ThreadSafeContext` | Thread-safe context for detection results |

See `asimov.base/SPEC.md` for full details.

### asimov.net

Networking for frame transmission:

| Item | Description |
|------|-------------|
| `TCPSender` | TCP frame sender |
| `TCPReceiver` | TCP frame receiver |
| `UDPSender` | UDP frame sender |
| `UDPReceiver` | UDP frame receiver |
| `Packet`, `FramePacket` | Packet classes |
| `encode_packet`, `decode_packet` | Packet encoding |

See `asimov.net/SPEC.md` for full details.

### asimov.modules

Computer vision modules:

| Module | Description |
|--------|-------------|
| `hand` | MediaPipe hand detection |
| `face` | FaceMesh face detection |
| `indexfingertip` | Index fingertip tracking |
| `rect` | Rectangle rendering |
| `rect_touch` | Touch detection |
| `eyes_next` | Eye privacy bars |
| `fps_overlay` | FPS counter overlay |
| `glitch` | Glitch visual effects |
| `motionblur` | Motion blur effect |
| `float_card` | Floating card overlay |
| `float_playingcard` | Playing card overlay |

See `asimov.modules/SPEC.md` for full details.

### asimov.playingcard

Playing card detection:

| Item | Description |
|------|-------------|
| `init` | Initialize card set |
| `detect` | Detect cards in frame |
| `draw` | Draw card overlay |
| `load` | Load card set |

See `asimov.playingcard/SPEC.md` for full details.

## Usage Examples

### Basic Import

```python
import asimov
from asimov import io, base, net, modules, playingcard
```

### Terminal Output

```python
from asimov import io

io.echo("{green}Success!{reset}")
io.echo("{bold}Warning: {yellow}Low memory{/reset}")
io.echo("{bgblue}{white}Press any key to continue...{/all}")
```

### Running a Module

```python
from asimov.base import module

# Load and run a module
m = module.load(args, "modules.hand")
module.run(args, m)
```

### Network Frame Transmission

```python
from asimov import net

sender = net.TCPSender("127.0.0.1", 6000)
sender.connect()
sender.send_frame(frame, frame_id=1)
```

### Detection Pipeline

```python
from asimov import io
from asimov.base.common import ThreadSafeContext
from asimov.modules import hand, face

context = ThreadSafeContext()

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # Run detection modules
    hand.detect(frame, context)
    face.detect(frame, context)
    
    # Draw overlays
    hand.draw(frame, context)
    
    cv2.imshow("Preview", frame)
```

## Configuration

Configuration is managed through `asimov.conf`:

```python
from asimov import conf

# Capture settings
conf.CAPTURE_DEVICE = 0
conf.CAPTURE_WIDTH = 640
conf.CAPTURE_HEIGHT = 480
conf.CAPTURE_FPS = 30

# Window settings
conf.WINDOW_NAME = "Asimov Preview"
```

Module-specific configuration is in `asimov.conf`:

```python
from asimov import conf

# Hand detection
conf.HAND["DETECTION"]["MAX_HANDS"] = 2
conf.HAND["FILTER"]["MIN_CUTOFF"] = 0.5
```

Network configuration is in `asimov.net.conf`:

```python
from asimov.net import conf

conf.DEFAULT_PORT = 5000
conf.COMPRESSION_ENABLED = True
```

## Module Lifecycle

Asimov modules follow a standard lifecycle:

1. **init(args)** - Initialize resources
2. **access(args, op)** - Check operation permission
3. **buildargs(args)** - Build argument parser
4. **main(args)** - Execute main logic

Detection modules also implement:

- **detect(frame, context)** - Run detection, publish to context
- **draw(frame, context)** - Draw overlays on frame

## Context System

Modules communicate through a `ThreadSafeContext` object:

```python
from asimov.base.common import ThreadSafeContext

context = ThreadSafeContext()

# Module publishes results
hand.detect(frame, context)
face.detect(frame, context)

# Other modules consume results
hands = context.get("HAND", {}).get("hands", [])
faces = context.get("FACE", {}).get("faces", [])
```

## Dependencies

- `numpy` - Numerical operations
- `opencv-python` - Computer vision
- `cvzone` - Hand/Face detection wrappers
- `mediapipe` - ML models for hand/face
- `PyOpenGL` - OpenGL rendering
- `PyGLM` - Math utilities
