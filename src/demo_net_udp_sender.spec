# demo_udp_sender Specification

## Overview

`demo_udp_sender` is a more feature-complete UDP frame sender demo with configurable frame intervals and grid dimensions.

## Usage

```bash
python demo_udp_sender.py [options]
```

## Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--host` | str | "127.0.0.1" | Target host |
| `--port` | int | 5000 | Target port |
| `--bind-port` | int | 0 | Local bind port (0=OS assigned) |
| `--capture-device` | int | CAPTURE_DEVICE | Camera device index |
| `--capture-width` | int | CAPTURE_WIDTH | Frame width |
| `--capture-height` | int | CAPTURE_HEIGHT | Frame height |
| `--capture-fps` | int | CAPTURE_FPS | Capture FPS |
| `--send_frames` | flag | True | Enable frame sending |
| `--frame_interval` | float | 1/30.0 | Seconds between frames |
| `--cols` | int | 0 | Grid columns (0=auto) |
| `--rows` | int | 0 | Grid rows (0=auto) |
| `--full-frame` | flag | False | Send full frame (not just changes) |
| `--compress` | flag | False | Enable zlib compression |

## Features

- Configurable frame rate via `--frame_interval`
- Separate bind port for multi-homed systems
- Delta compression by default
- Non-square grid support

## Behavior

1. Opens video capture with specified dimensions
2. Sends first frame as full frame
3. Subsequent frames use delta compression (only changed blocks)
4. Configurable via CLI arguments

## Exit

- Ctrl+C to stop
- Cleanup: closes socket, releases camera
