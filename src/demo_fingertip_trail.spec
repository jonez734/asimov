# demo_fingertip_trail Specification

## Overview

`demo_fingertip_trail` demonstrates fingertip tracking with trail visualization using MediaPipe hand tracking.

## Usage

```bash
python demo_fingertip_trail.py [options]
```

## Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--device` | int | 0 | Camera device index |

## Features

- MediaPipe hand landmark detection
- Fingertip tracking with OneEuroFilter smoothing
- Trail visualization showing fingertip movement history
- Real-time FPS overlay

## Exit

- Press ESC to quit
