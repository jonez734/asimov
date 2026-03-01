# demo_float_playingcard_2 Specification

## Overview

`demo_float_playingcard_2` demonstrates floating playing cards with glitch effects on detected hands using cvzone HandTrackingModule.

## Usage

```bash
python demo_float_playingcard_2.py [options]
```

## Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--device` | int | 0 | Camera device index |

## Features

- cvzone HandDetector for hand tracking
- Floating card overlay on palms
- Glitch effects (RGB shift, scan lines, noise)
- Configurable opacity and card size

## Exit

- Press ESC to quit
