# demo_net_camera Specification

## Overview

`demo_net_camera` demonstrates streaming camera capture over UDP with automatic chunking. Includes sender and receiver components.

## Usage

### Sender

```bash
python demo_net_camera_send.py [options]
```

### Receiver

```bash
python demo_net_camera_recv.py [options]
```

## Sender Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--host` | str | "127.0.0.1" | Target host |
| `--port` | int | 5000 | Target port |
| `--device` | str | str(conf.CAPTURE_DEVICE) | Camera device (int index or video path) |
| `--width` | int | conf.CAPTURE_WIDTH | Frame width |
| `--height` | int | conf.CAPTURE_HEIGHT | Frame height |
| `--fps` | int | conf.CAPTURE_FPS | Capture FPS |
| `--test` | flag | False | Use animated test pattern instead of camera |
| `--debug` | flag | False | Show debug info (frame shape) |

## Receiver Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--host` | str | "127.0.0.1" | Bind host |
| `--port` | int | 5000 | Bind port |
| `--debug` | flag | False | Show debug info (frame shape) |

## Features

- **Automatic chunking**: Calculates optimal block size using GCD of frame dimensions
- **Full frame transmission**: Always sends complete frames (no delta compression)
- **Auto-batching**: Groups multiple blocks into single UDP packets for efficiency
- **Non-square grid**: Automatically determines cols x rows grid based on frame size
- **Test pattern**: Animated pattern with gradient, color bars, bouncing ball, and rotating square

## Chunking Algorithm

1. Calculate GCD of width and height
2. Determine grid: `cols = width // block_size`, `rows = height // block_size`
3. Example: 640x480 with GCD 64 → 10x7 grid = 70 blocks

## Auto-Batching

- Calculates max blocks per UDP packet based on block size
- Max UDP payload: 65442 bytes
- Header overhead: 35 bytes (includes original width/height for accurate frame reconstruction)
- Example: 64x64 blocks (12288 bytes) → 5 blocks/packet

## Test Pattern

When `--test` is specified, generates an animated test pattern including:
- Animated gradient background (shifts left-right)
- Color bars (moves up-down)
- Bouncing ball
- Rotating square in center

Animation is time-based, so it runs at the same speed regardless of FPS setting.

## Example

```bash
# Terminal 1: Start receiver
python demo_net_camera_recv.py --port 5000

# Terminal 2: Start sender with test pattern
python demo_net_camera_send.py --host 127.0.0.1 --port 5000 --test

# Or with real camera
python demo_net_camera_send.py --host 127.0.0.1 --port 5000
```

## Exit

- Sender: Press ESC
- Receiver: Press 'q'
