# demo_float_playingcard Specification

## Overview

`demo_float_playingcard` demonstrates floating playing card visualization on detected hand palms using MediaPipe hand tracking.

## Usage

```bash
python demo_float_playingcard.py --card <card_image> [options]
```

## Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--device` | int | conf.CAP_DEVICE | Camera device index |
| `--card` | str | (required) | Card PNG filename to load |

## Features

- MediaPipe hand landmark detection
- Palm tracking for floating card positioning
- Card perspective warping to match hand orientation
- Real-time card overlay on hand

## Exit

- Press ESC to quit
