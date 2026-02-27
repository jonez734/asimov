# demo_pyvirtualcam Specification

## Overview

`demo_pyvirtualcam` demonstrates virtual camera output using pyvirtualcam for streaming to applications like Zoom/OBS.

## Usage

```bash
python demo_pyvirtualcam.py [options]
```

## Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--device` | int | 0 | Camera device index |
| `--width` | int | 640 | Frame width |
| `--height` | int | 480 | Frame height |
| `--fps` | int | 30 | Frames per second |

## Features

- Virtual camera output via pyvirtualcam
- Real-time video capture
- Compatible with Zoom, OBS, etc.

## Exit

- Press ESC to quit
