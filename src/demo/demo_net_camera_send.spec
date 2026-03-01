# demo_net_camera_send Specification

## Overview

`demo_net_camera_send` demonstrates sending camera capture over UDP with automatic chunking (sender side). See demo_net_camera.spec for full documentation.

## Usage

```bash
python demo_net_camera_send.py [options]
```

## Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--host` | str | "127.0.0.1" | Target host |
| `--port` | int | 5000 | Target port |
| `--device` | str | conf.CAPTURE_DEVICE | Camera device |
| `--width` | int | conf.CAPTURE_WIDTH | Frame width |
| `--height` | int | conf.CAPTURE_HEIGHT | Frame height |
| `--fps` | int | conf.CAPTURE_FPS | Capture FPS |
| `--test` | flag | False | Use test pattern |
| `--debug` | flag | False | Show debug info |

## Exit

- Press ESC to quit
