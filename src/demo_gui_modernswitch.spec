# ModernSwitch Widget Specification

## Overview
A custom Tkinter toggle switch widget with smooth animations, mimicking mobile OS pill-shaped toggles.

## Class
`ModernSwitch(tk.Canvas)`

## Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| parent | tk widget | required | Parent widget |
| height | int | 40 | Widget height in pixels |
| width | int | height * 2.2 | Widget width (computed if not provided) |
| variable | tk.BooleanVar | None | Optional BooleanVar to bind |
| command | callable | None | Optional callback on toggle |
| enabled | bool | True | Whether widget responds to input |

## Visual Design
- **Track**: Pill-shaped oval
  - ON: Green (#2ecc71)
  - OFF: Red (#e74c3c)
  - DISABLED: Gray (#cccccc)
- **Thumb**: Circular slider
  - Normal: White (#ffffff)
  - DISABLED: Gray (#aaaaaa)
- **Dimensions**: Calculated relative to height
  - Thumb diameter: height * 0.8
  - Thumb margin: (height - thumb_diameter) / 2
  - Thumb position: Left (OFF) or Right (ON)

## State Management
- Uses `BooleanVar` via `variable` parameter
- External variable changes tracked via `trace_add("write", ...)`
- `enabled` property controls interactivity and colors

## Animation
- **Duration**: ~160ms (12 steps at ~13ms each)
- **Effects**: Simultaneous thumb slide + color interpolation
- **Non-blocking**: Uses `root.after()` for smooth GUI
- **Rapid clicks**: Cancels existing animation before starting new one via `after_cancel`

## Public Methods
| Method | Description |
|--------|-------------|
| `get()` | Returns current state (True/False) |
| `set(value)` | Programmatically set state |
| `enabled` property | Get/set enabled state |

## Events
- Click: Toggle state if enabled
- External variable change: Animate to match variable value

## Exit Behavior (Demo)
- ESC key: Exit
- Q/q key: Exit  
- Window close button: Exit

## Usage Example
```python
import tkinter as tk
from modern_switch import ModernSwitch

root = tk.Tk()
var = tk.BooleanVar(value=True)

switch = ModernSwitch(root, variable=var, height=40)
switch.pack()

root.mainloop()
```
