# demo_fingertip_detect_rank_suit Specification

## Overview

`demo_fingertip_detect_rank_suit` demonstrates detecting playing card rank and suit using MediaPipe hand tracking and OpenCV contour detection.

## Usage

```bash
python demo_fingertip_detect_rank_suit.py [options]
```

## Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--device` | int | 0 | Camera device index |

## Features

- MediaPipe hand landmark detection
- Fingertip tracking with OneEuroFilter smoothing
- Card rectangle detection with aspect ratio filtering
- Card rank and suit identification via template matching
- Contour-based card boundary detection

## Exit

- Press ESC to quit
