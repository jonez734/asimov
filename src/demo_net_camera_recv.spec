# demo_net_camera_recv Specification

## Overview

`demo_net_camera_recv` demonstrates receiving camera frames over UDP with automatic chunking (receiver side). See demo_net_camera.spec for full documentation.

## Usage

```bash
python demo_net_camera_recv.py [options]
```

## Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--host` | str | "127.0.0.1" | Bind host |
| `--port` | int | 5000 | Bind port |
| `--debug` | flag | False | Show debug info |

## Exit

- Press 'q' to quit
