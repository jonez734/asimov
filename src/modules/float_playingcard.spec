# float_playingcard Specification

## Overview

`float_playingcard` is an Asimov overlay module that renders a floating playing card anchored to the user's hand. It supports two modes:
1. **Dashboard mode**: User selects rank/suit via dashboard UI
2. **Config mode**: Single card image loaded from filesystem

The card gently floats up/down with a per-hand phase offset, and supports glitch effects.

## Command Line Arguments

The module uses args from `asimov/__main__.py`:

| Argument | Default | Description |
|----------|---------|-------------|
| --basedir | $HOME/projects/playingcarddata | Base directory for card sets |
| --set-name | bicycle | Card set subdirectory name |

These are stored during `init(args)` and used to construct card paths.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Input Sources                          │
├─────────────────────────────────────────────────────────────┤
│  1. Command Line Args (--basedir, --set-name)              │
│     - Stored in module global during init()                │
│     - Used to construct card asset paths                  │
│                                                              │
│  2. Dashboard Config (rank, suit, opacity)                 │
│     - Set via ui_schema() fields                           │
│     - Passed to draw() via config= parameter              │
│                                                              │
│  3. conf.FLOAT_PLAYINGCARD (static config)                 │
│     - IMAGE: path to card image                           │
│     - SCALE, ROTATION, OPACITY                            │
│     - FLOAT_AMPLITUDE, FLOAT_FREQUENCY                    │
│                                                              │
│  4. Hand Detection (from hand module)                       │
│     - context.get("HAND")["hands"] (list of hands)        │
│     - Each hand has: bbox, center, lmList, type           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    detect(frame, context)                   │
├─────────────────────────────────────────────────────────────┤
│  1. Get hand center (try primary_hand, fallback to HAND)   │
│  2. Generate stable phase from hand position              │
│  3. Publish to context.card {center, scale, angle, phase}  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    draw(frame, context, config)            │
├─────────────────────────────────────────────────────────────┤
│  1. Load card image (dashboard or config)                 │
│  2. Apply scale/rotation                                   │
│  3. Compute floating offset (sin wave + phase)            │
│  4. Apply glitch effects (optional)                       │
│  5. Render RGBA layer to context.layers["card"]            │
└─────────────────────────────────────────────────────────────┘
```

## Configuration (conf.FLOAT_PLAYINGCARD)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| IMAGE | str | None | Full path to card image (None = use args fallback) |
| SCALE | float | 0.8 | Scale factor relative to hand width |
| ROTATION | float | 0 | Rotation angle in degrees |
| OPACITY | float | 0.8 | Overlay opacity (0.0-1.0) |
| FLOAT_AMPLITUDE | int | 12 | Vertical floating range in pixels |
| FLOAT_FREQUENCY | float | 0.5 | Floating animation speed in Hz |

## Dashboard UI Schema

```python
{
    "rank": {
        "type": "radio",
        "enum": ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"],
        "label": "Rank",
    },
    "suit": {
        "type": "radio",
        "enum": ["hearts", "diamonds", "clubs", "spades"],
        "label": "Suit",
    },
    "opacity": {
        "type": "float",
        "default": 0.8,
        "min": 0.1,
        "max": 1.0,
        "step": 0.05,
        "label": "Opacity",
    },
    "glitch": {
        "type": "bool",
        "default": True,
        "label": "Enable Glitch",
    },
}
```

The dashboard renders rank and suit as horizontal radio button groups for quick one-click selection.

When rank/suit are set, card loads from `{basedir}/sets/{set-name}/{rank}_of_{suit}.png`.  
When cleared (None), falls back to:
- `conf.FLOAT_PLAYINGCARD.IMAGE` if set
- Otherwise `{basedir}/sets/{set-name}/queen_of_spades.png`

## Module ABI

### detect(frame, context, **kw)
- **Input**: frame (np.ndarray), context (ThreadSafeContext)
- **Output**: Sets `context.card` dict with keys:
  - `center`: (x, y) hand center coordinates
  - `scale`: float from config
  - `angle`: float from config
  - `phase`: float [0, 2π) stable per hand position
- **Hand detection**: Reads from `context["HAND"]["hands"]` (list from cvzone HandDetector)
  - Each hand dict contains: `bbox`, `center`, `lmList`, `type`, `confidence`
  - Uses first hand in list if multiple hands detected
- **Graceful handling**: When hand module is not running or no hand detected:
  - If `context["HAND"]` is missing (hand module not loaded): sets `context.card = None`
  - If `context["HAND"]["hands"]` is empty: sets `context.card = None`
  - No error raised

### draw(frame, context, config=None, **kw)
- **Input**: 
  - frame: BGR np.ndarray
  - context: ThreadSafeContext with `.card` attribute
  - config: Optional dict with rank/suit/opacity
- **Output**: Returns frame (layer stored in `context.layers["card"]`)
- **Graceful handling**:
  - If `context.card` is None (no hand detected or hand module disabled): returns frame unchanged
  - If no card image loaded: returns frame unchanged
  - If card image fails to load: returns frame unchanged (silent)
- **Behavior**:
  1. Load card image (dashboard or config source)
  2. Resize based on card["scale"]
  3. Rotate if card["angle"] != 0
  4. Apply floating offset using sin(t * freq + phase) * amplitude
  5. Run glitch scheduler, apply if active
  6. Composite to RGBA layer, store in `context.layers["card"]`

### init(args, context=None, **kwargs) -> bool
- Captures and stores command line args:
  - `_basedir`: expanded from `args.basedir` (default: `$HOME/projects/playingcarddata`)
  - `_set_name`: from `args.set_name` (default: `bicycle`)
- Initializes glitch framework:
  - `glitch.set_max_concurrent(2)`
  - Registers: scanlines, vhs_warp, ghost

### ui_schema() -> dict
- Returns dashboard config schema (see above)

## Lifecycle Hooks

| Hook | Purpose |
|------|---------|
| init | Setup glitch system |
| access | Always returns True |
| buildargs | Returns None |
| main | Returns True |

## Context Layers

After draw(), the module creates:
- `context.layers["card"]`: RGBA layer (h, w, 4) uint8

This layer should be composited by the render loop.

## Glitch Effects

Registered in init():
- **scanlines**: Horizontal scanlines
- **vhs_warp**: VHS-style warp (intensity=7, freq=3.0, speed=1.5)
- **ghost**: Ghosting effect (alpha=0.3, shift=8)

Applied in draw() when `glitch.is_any_glitch_running()` is true.

## File Loading

Card paths are constructed in this priority order:

1. **Dashboard Mode** (rank + suit set via ui_schema):
   ```
   {basedir}/sets/{set-name}/{rank}_of_{suit}.png
   ```

2. **Config Mode** (conf.FLOAT_PLAYINGCARD.IMAGE if set):
   ```
   {IMAGE}  # Full path with $HOME expansion
   ```

3. **Default Fallback** (both unset):
   ```
   {basedir}/sets/{set-name}/queen_of_spades.png
   ```

**Module globals** (set in `init(args)`):
- `_basedir`: Expanded path from `--basedir` arg
- `_set_name`: Value from `--set-name` arg

Card images must be RGBA (4-channel). If loaded as 3-channel, alpha channel is synthesized as 255.

## Floating Animation

The floating motion uses a sine wave with per-hand phase offset:

```python
dy = sin(2π * frequency * t + phase) * amplitude
```

- **phase**: Generated from hand position hash (stable across frames for same hand position)
- **frequency**: conf.FLOAT_PLAYINGCARD.FLOAT_FREQUENCY (default 0.5 Hz)
- **amplitude**: conf.FLOAT_PLAYINGCARD.FLOAT_AMPLITUDE (default 12 pixels)

## Usage in SCENE

```python
SCENE = {
    "name": "float_card",
    "modules": [
        {"name": "hand", "module": "asimov.modules.hand", "conf": {}},
        {"name": "float_playingcard", "module": "asimov.modules.float_playingcard", "conf": {}},
    ],
    "conf": {
        "HAND": {"MAX_HANDS": 1},
        "FLOAT_PLAYINGCARD": {"OPACITY": 0.85},
    },
}
```

## Dependencies

- cv2 (OpenCV)
- numpy
- asimov.conf
- asimov.common.ThreadSafeContext
- asimov.util.safe_path
- asimov.glitch (optional, gracefully handled)
- hashlib (stdlib)
- math (stdlib)
- time (stdlib)
