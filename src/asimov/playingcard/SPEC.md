# asimov.playingcard Specification

## Overview

`asimov.playingcard` provides playing card detection using template matching. It detects playing cards from video frames using precomputed template data.

## Package Structure

```
playingcard/
├── __init__.py                  # Main package exports
├── asimov_playingcard/
│   ├── __init__.py             # Module initialization
│   ├── cards.py                # Card data structures
│   ├── detect.py               # Detection logic
│   ├── set.py                  # Card set loading
│   ├── templates.py             # Template management
│   ├── train.py                # Training utilities
│   ├── util.py                 # Utility functions
│   └── common.py               # Common utilities
```

## Module Functions

### __init__.py

The package provides these public functions:

| Function | Signature | Description |
|----------|-----------|-------------|
| `init` | `(args=None, context=None, **kwargs)` | Load playing card set from args or config |
| `access` | `(args, op, **kwargs)` | Check operation access |
| `buildargs` | `(args, **kwargs)` | Build argument parser |
| `main` | `(args, **kwargs)` | Main execution |
| `detect` | `(frame, context, **kwargs)` | Detect playing card in frame |
| `draw` | `(frame, context)` | Draw overlay info for detected card |
| `load` | `(basedir, set_name)` | Load card set (alias for load_set) |
| `load_set` | `(basedir, set_name)` | Load card set from directory |
| `card_set` | `(basedir, set_name)` | Alias for load_set |

### cards.py

Card data structures and constants:

| Item | Type | Description |
|------|------|-------------|
| `RANKS` | list | Card ranks ["A", "2", "3", ..., "K"] |
| `SUITS` | list | Card suits ["hearts", "diamonds", "clubs", "spades"] |
| `RANK_DISPLAY` | dict | Display symbols for ranks |
| `SUIT_DISPLAY` | dict | Display symbols for suits |
| `SUIT_SYMBOLS` | dict | Unicode suit symbols |

Functions:
- `load_card_image(card_name, basedir)` - Load card image file
- `get_card_path(card_name, basedir)` - Get path to card image
- `parse_card_string(s)` - Parse card string like "AH" to rank/suit
- `is_valid_card(card_string)` - Validate card string format

### detect.py

Detection logic:

| Function | Signature | Description |
|----------|-----------|-------------|
| `detect` | `(frame, context, **kwargs)` | Detect cards in frame |
| `detect_card` | `(frame, templates)` | Core detection algorithm |
| `match_template` | `(frame, template)` | Match template against frame |

### set.py

Card set management:

| Function | Signature | Description |
|----------|-----------|-------------|
| `load` | `(basedir, set_name)` | Load card set from directory |
| `load_set` | `(basedir, set_name)` | Load card set |
| `get_card` | `(rank, suit)` | Get card by rank/suit |

### templates.py

Template management:

| Function | Signature | Description |
|----------|-----------|-------------|
| `load_templates` | `(basedir, set_name)` | Load all templates for a set |
| `get_template` | `(rank, suit)` | Get specific template |
| `add_template` | `(rank, suit, image)` | Add template to registry |

### train.py

Training utilities for creating new templates:

| Function | Signature | Description |
|----------|-----------|-------------|
| `train` | `(basedir, set_name)` | Train templates from images |
| `extract_card` | `(image)` | Extract card from image |
| `normalize_card` | `(card_image)` | Normalize card image |

### util.py

Utility functions:

| Function | Signature | Description |
|----------|-----------|-------------|
| `resize_card` | `(image, size)` | Resize card image |
| `rotate_card` | `(image, angle)` | Rotate card image |
| `preprocess` | `(image)` | Preprocess for template matching |

## Configuration

Configuration is read from `conf.PLAYINGCARD`:

```python
PLAYINGCARD = {
    "BASEDIR": "$HOME/projects/playingcarddata",  # Template directory
    "SET_NAME": "bicycle",                         # Card set name
    "DETECTION_THRESHOLD": 0.8,                    # Match threshold
}
```

## Usage Examples

### Basic Detection

```python
from asimov.playingcard import init, detect, draw

# Initialize card set
init(args)

# In frame loop
detect(frame, context)
result = context.get("playingcard_detected")

# Draw overlay
frame = draw(frame, context)
```

### Loading Card Sets

```python
from asimov.playingcard import load_set

# Load bicycle card set
load_set("$HOME/projects/playingcarddata", "bicycle")

# Load custom set
load_set("/path/to/cards", "custom")
```

### Manual Detection

```python
from asimov.playingcard import detect, templates

# Load templates
cards = load_set(basedir, set_name)

# Detect in frame
detected = detect_card(frame, templates)

if detected:
    print(f"Detected: {detected['name']}, confidence: {detected['score']}")
```
