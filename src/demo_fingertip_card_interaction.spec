# demo_fingertip_card_interaction Specification

## Overview

`demo_fingertip_card_interaction` demonstrates fingertip-based card interaction using MediaPipe hand tracking and OpenCV card detection.

## Usage

```bash
python demo_fingertip_card_interaction.py [options]
```

## Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--device` | int | 0 | Camera device index |

## Features

- MediaPipe hand landmark detection
- Fingertip tracking with OneEuroFilter smoothing
- Card rectangle detection from video frames
- Interaction detection between fingertip and cards
- Real-time FPS overlay

## Exit

- Press ESC to quit
