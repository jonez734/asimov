# send_frame_demo Specification

## Overview

`send_frame_demo` demonstrates sending cv2 video frames over UDP using asimov's frame transmission system with delta compression and auto-batching.

## Usage

```bash
python send_frame_demo.py [options]
```

## Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--capture-device` | int | CAPTURE_DEVICE | Camera device index |
| `--capture-width` | int | CAPTURE_WIDTH | Frame width |
| `--capture-height` | int | CAPTURE_HEIGHT | Frame height |
| `--capture-fps` | int | CAPTURE_FPS | Capture FPS |
| `--host` | str | "127.0.0.1" | Target host |
| `--port` | int | 5000 | Target port |
| `--cols` | int | 0 | Grid columns (0=auto) |
| `--rows` | int | 0 | Grid rows (0=auto) |
| `--full-frame` | flag | False | Send full frame (not just changes) |
| `--compress` | flag | False | Enable zlib compression |

## Behavior

1. Opens video capture device
2. Configures capture with specified dimensions
3. **First frame**: Sends full frame (resets `prev_frame` to None)
4. **Subsequent frames**: Sends only changed blocks (delta compression)
5. **Auto-batching**: Groups multiple blocks into single UDP packets to maximize bandwidth

## Delta Compression

By default, only blocks that differ from the previous frame are transmitted:
- Uses `asimov.util.get_changed_blocks()` to detect differences
- Applies changes to previous frame on receiver side
- Significantly reduces bandwidth for static scenes

## Auto-Batching

Automatically calculates optimal number of blocks per packet:
- Max UDP payload: 65442 bytes
- Header: 37 bytes
- Example: 64x64 blocks = 12288 bytes → 5 blocks/packet

## Exit

- Press ESC to quit
- Cleanup: releases camera, closes socket, destroys windows
