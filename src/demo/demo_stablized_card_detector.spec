# demo_stablized_card_detector Specification

## Overview

`demo_stablized_card_detector` demonstrates stabilized playing card detection with smoothing filters.

## Usage

```bash
python demo_stablized_card_detect.py [options]
```

## Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--device` | int | 0 | Camera device index |

## Features

- Stabilized card detection using OneEuroFilter
- Reduced jitter in detection
- Smooth tracking visualization

## Exit

- Press ESC to quit
